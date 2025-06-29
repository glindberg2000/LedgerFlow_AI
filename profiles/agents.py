# Agent, Tool, and LLMConfig constants and bootstrapping utilities
import os
import importlib.util
from pathlib import Path
from django.apps import apps
from django.conf import settings

# --- Agent/LLM/Tool Names ---
PAYEE_LOOKUP_AGENT = "Payee Lookup Agent"
CLASSIFICATION_AGENT = "Classification Agent"
BUSINESS_PROFILE_AGENT = "Business Profile Generation Agent"
ESCALATION_AGENT = "Classification Escalation Agent"

LLM_FAST_MODEL = "gpt-4.1-mini"
LLM_PRECISE_MODEL = "o4-mini"
LLM_PROVIDER = "openai"

# --- Tool Discovery ---
TOOL_DIRS = [
    Path(settings.BASE_DIR) / "tools",
]


def discover_tools():
    """Scan the tools directory for Python modules with callable tool functions."""
    tool_defs = []
    for tool_dir in TOOL_DIRS:
        for root, dirs, files in os.walk(tool_dir):
            for file in files:
                if file.endswith(".py") and not file.startswith("__"):
                    module_path = Path(root) / file
                    module_name = module_path.stem
                    try:
                        spec = importlib.util.spec_from_file_location(
                            module_name, module_path
                        )
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)
                        # Look for a function matching the module name
                        if hasattr(module, module_name):
                            func = getattr(module, module_name)
                            if callable(func):
                                desc = getattr(
                                    module, "description", func.__doc__ or ""
                                )
                                tool_defs.append(
                                    {
                                        "name": module_name,
                                        "description": desc,
                                        "module_path": str(
                                            module_path.relative_to(settings.BASE_DIR)
                                        ),
                                    }
                                )
                    except Exception as e:
                        continue  # Ignore broken modules
    return tool_defs


# --- Bootstrapping Utilities ---
def bootstrap_tools_and_agents():
    """Create default tools, LLM configs, and agents if missing. Assign tools to agents as needed."""
    Tool = apps.get_model("profiles", "Tool")
    Agent = apps.get_model("profiles", "Agent")
    LLMConfig = apps.get_model("profiles", "LLMConfig")

    # 1. LLM Configs
    llm_fast, _ = LLMConfig.objects.get_or_create(
        provider=LLM_PROVIDER, model=LLM_FAST_MODEL
    )
    llm_precise, _ = LLMConfig.objects.get_or_create(
        provider=LLM_PROVIDER, model=LLM_PRECISE_MODEL
    )

    # 2. Tools
    discovered = discover_tools()
    tool_objs = {}
    for tool in discovered:
        obj, _ = Tool.objects.get_or_create(
            name=tool["name"],
            defaults={
                "description": tool["description"],
                "module_path": tool["module_path"],
            },
        )
        tool_objs[tool["name"]] = obj

    # 3. Agents
    # Prompts can be loaded from migrations or set to sensible defaults
    default_prompts = {
        PAYEE_LOOKUP_AGENT: "You are a transaction analysis assistant. Your task is to identify the payee/merchant from transaction descriptions using available tools.",
        CLASSIFICATION_AGENT: "You are an expert in business expense classification and tax preparation. Classify each transaction as business or personal, assign worksheet and category, and provide reasoning.",
        BUSINESS_PROFILE_AGENT: "You are an AI assistant for generating business profiles from user descriptions.",
        ESCALATION_AGENT: "You are a senior reviewer for difficult or ambiguous expense classifications. Apply advanced scrutiny and flag for review if unsure.",
    }
    agents = {
        PAYEE_LOOKUP_AGENT: {
            "llm": llm_fast,
            "prompt": default_prompts[PAYEE_LOOKUP_AGENT],
        },
        CLASSIFICATION_AGENT: {
            "llm": llm_fast,
            "prompt": default_prompts[CLASSIFICATION_AGENT],
        },
        BUSINESS_PROFILE_AGENT: {
            "llm": llm_precise,
            "prompt": default_prompts[BUSINESS_PROFILE_AGENT],
        },
        ESCALATION_AGENT: {
            "llm": llm_precise,
            "prompt": default_prompts[ESCALATION_AGENT],
        },
    }
    for name, config in agents.items():
        agent, _ = Agent.objects.get_or_create(
            name=name,
            defaults={
                "purpose": name,
                "prompt": config["prompt"],
                "llm": config["llm"],
            },
        )
        # Assign tools to Payee Lookup Agent only
        if name == PAYEE_LOOKUP_AGENT:
            # Assign all tools except those requiring extra config (e.g., brave_search)
            for tool_name, tool_obj in tool_objs.items():
                if tool_name != "brave_search":
                    agent.tools.add(tool_obj)
        agent.save()
