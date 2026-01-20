import yaml

def load_rules():
    with open("isr_rules.yaml") as f:
        return yaml.safe_load(f)