#!/usr/bin/env node
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  ListToolsRequestSchema,
  CallToolRequestSchema,
  ErrorCode,
  McpError
} from "@modelcontextprotocol/sdk/types.js";
import path from 'path';
import { fileURLToPath } from 'url';
import dotenv from 'dotenv';
import { z } from 'zod';
import { zodToJsonSchema } from 'zod-to-json-schema';
import { callGrok } from './utils.js';

// Initialize environment
import { dirname } from 'path';
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
dotenv.config();
console.error("Grok MCP server initializing...");

// Schema definitions
const GrokQuickSchema = z.object({
  prompt: z.string().describe("Analysis prompt for Grok"),
  model: z.string().optional().default("grok-4-latest").describe("Grok model to use")
});

const GrokAnalyzeSchema = z.object({
  prompt: z.string().describe("Analysis prompt for Grok"),
  model: z.string().optional().default("grok-4-latest").describe("Grok model to use"),
  context_dir: z.string().optional().default("/Users/greg/repos/CryptoTaxCalc_Coder1").describe("Directory context for analysis")
});

// Type definitions
type GrokQuickArgs = z.infer<typeof GrokQuickSchema>;
type GrokAnalyzeArgs = z.infer<typeof GrokAnalyzeSchema>;

// Main function
async function main() {
  // Check if GROK_API_KEY is set
  if (!process.env.GROK_API_KEY) {
    console.error('Error: GROK_API_KEY environment variable is not set');
    console.error('Please set it as: export GROK_API_KEY=your_api_key_here');
    process.exit(1);
  }

  // Create MCP server
  const server = new Server({
    name: "grok-mcp-server",
    version: "1.0.0"
  }, {
    capabilities: {
      tools: {}
    }
  });

  // Set up error handling
  server.onerror = (error) => {
    console.error("Grok MCP Server Error:", error);
  };

  process.on('SIGINT', async () => {
    await server.close();
    process.exit(0);
  });

  // Set up tool handlers
  server.setRequestHandler(
    ListToolsRequestSchema,
    async () => {
      console.error("Handling ListToolsRequest");
      return {
        tools: [
          {
            name: "grok_quick",
            description: "Quick analysis using Grok AI without directory context",
            inputSchema: zodToJsonSchema(GrokQuickSchema),
          },
          {
            name: "grok_analyze",
            description: "Analyze code/data using Grok AI with CryptoTaxCalc directory context",
            inputSchema: zodToJsonSchema(GrokAnalyzeSchema),
          },
        ]
      };
    }
  );

  server.setRequestHandler(
    CallToolRequestSchema,
    async (request) => {
      console.error("Handling CallToolRequest:", JSON.stringify(request.params));
      
      try {
        switch (request.params.name) {
          case "grok_quick": {
            const args = GrokQuickSchema.parse(request.params.arguments) as GrokQuickArgs;
            console.error(`Grok Quick: "${args.prompt.substring(0, 100)}..."`);
            
            const result = await callGrok(args.prompt, {
              model: args.model
            });
            
            return {
              content: [{
                type: "text",
                text: result.content
              }]
            };
          }
          
          case "grok_analyze": {
            const args = GrokAnalyzeSchema.parse(request.params.arguments) as GrokAnalyzeArgs;
            console.error(`Grok Analyze: "${args.prompt.substring(0, 100)}..." in ${args.context_dir}`);
            
            const result = await callGrok(args.prompt, {
              model: args.model,
              context_dir: args.context_dir
            });
            
            return {
              content: [{
                type: "text",
                text: result.content
              }]
            };
          }
          
          default:
            throw new McpError(
              ErrorCode.MethodNotFound,
              `Unknown tool: ${request.params.name}`
            );
        }
      } catch (error) {
        console.error("ERROR during Grok CLI call:", error);
        
        return {
          content: [{
            type: "text",
            text: `Grok CLI error: ${error instanceof Error ? error.message : String(error)}`
          }],
          isError: true
        };
      }
    }
  );

  // Start the server
  console.error("Starting Grok MCP server");
  
  try {
    const transport = new StdioServerTransport();
    console.error("StdioServerTransport created");
    
    await server.connect(transport);
    console.error("Server connected to transport");
    
    console.error("Grok MCP server running on stdio");
  } catch (error) {
    console.error("ERROR starting server:", error);
    throw error;
  }
}

// Main execution
main().catch(error => {
  console.error("Server runtime error:", error);
  process.exit(1);
});