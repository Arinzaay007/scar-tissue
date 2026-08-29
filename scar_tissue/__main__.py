import sys, json
from .agent import run_agent

EXAMPLE_CODE = """
def get_user(user_id):
    users = fetch_all_users()
    for i in range(len(users)):
        if users[i].id == user_id:
            return users[i]

def process_data(data=[]):
    data.append(1)
    return data

password = "super_secret_password_123"
"""

def main():
    if len(sys.argv) < 2:
        print("Scar Tissue - The Agent That Remembers What Broke You")
        print()
        print("Usage: python -m scar_tissue demo")
        return
    cmd = sys.argv[1]
    if cmd == "demo":
        print("Scar Tissue - Demo")
        print()
        result = run_agent(EXAMPLE_CODE, user_id="demo-user")
        if result["warning"]:
            print(result["warning"])
            receipt = json.dumps(result["receipt"], indent=2)
            print(f"\nReceipt: {receipt}")
        else:
            print("No anti-patterns detected.")

if __name__ == "__main__":
    main()
