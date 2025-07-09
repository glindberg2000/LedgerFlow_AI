import json
import os

WORKBOOK_CONFIG_PATH = os.path.join(
    os.path.dirname(__file__), "../bootstrap/special_page_configs.json"
)
AD_HOC_CONFIG_PATH = os.path.join(
    os.path.dirname(__file__), "../bootstrap/ad_hoc_binder_items.json"
)


def load_workbook_form_options():
    with open(WORKBOOK_CONFIG_PATH, "r") as f:
        data = json.load(f)
    options = []
    for form_id, config in data.items():
        if form_id == "default":
            continue
        label = config.get("Title", form_id)
        options.append({"form_id": form_id, "label": label, "source": "workbook"})
    return options


def load_ad_hoc_form_options():
    with open(AD_HOC_CONFIG_PATH, "r") as f:
        data = json.load(f)
    for item in data:
        item["source"] = "ad_hoc"
    return data


def get_all_binder_item_options(grouped=False):
    workbook = load_workbook_form_options()
    ad_hoc = load_ad_hoc_form_options()
    if grouped:
        return {"workbook": workbook, "ad_hoc": ad_hoc}
    return workbook + ad_hoc
