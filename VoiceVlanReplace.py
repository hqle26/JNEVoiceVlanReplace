import os
import re
import getpass
from netmiko import ConnectHandler

TEMPLATE_DIR = "templates"
CONFIG_DIR = "configs"

def get_interfaces_and_vlans(net_connect, old_vlan):

    interfaces = []

    output = net_connect.send_command("show int status")

    intf_lines = [line for line in output.splitlines() if re.match(r'^[A-Za-z]+[1-9/0]+', line)]
    for intf_line in intf_lines:
        intf_name = intf_line.split()[0]

        # Skip unwanted interfaces
        if intf_name.startswith("Ap"):
            continue
        if intf_name.startswith("Vlan"):
            continue
        if re.search(r"/1/", intf_name):  # skip anything with /1/ in the middle
            continue

        # Get the config of this interface
        run_output = net_connect.send_command(f"show run interface {intf_name}")

        # Look for switchport access vlan
        vlan_match = re.search(f"switchport voice vlan {old_vlan}", run_output)
        if vlan_match:
            interfaces.append(intf_name)
        print(interfaces)

    return interfaces

def generate_intf_config(interfaces, new_vlan):

    template_path = os.path.join(TEMPLATE_DIR, "intf_config.txt")
    with open(template_path, "r") as f:
        template = f.read()

    configs = []
    for intf in interfaces:
        cfg = template.replace("{{{intf}}}", intf).replace("{{{vlan}}}", new_vlan)
        configs.append(cfg)

    return "\n".join(configs)

def main():
    username = input("Enter username: ").strip()
    password = getpass.getpass("Enter password: ").strip()

    while True:
        host_ip = input("\nEnter host IP (or 'e' to end): ").strip()
        existing_voice_vlan = input("Enter existing voice vlan: ").strip()
        new_voice_vlan = input("Enter new voice vlan: ").strip()

        if host_ip.lower() == "e":
            print("Bye!")
            break

        device = {
            "device_type": "cisco_ios",
            "ip": host_ip,
            "username": username,
            "password": password,
            "secret": password
        }
        print(f"Connecting to {host_ip}...")

        try:
            net_connect = ConnectHandler(**device)
            net_connect.enable()
            hostname = net_connect.find_prompt().strip('#>')
            interfaces = get_interfaces_and_vlans(net_connect,existing_voice_vlan)
            net_connect.disconnect()

            if not interfaces:
                print("No valid interfaces found.")
                continue

            intf_config_text = generate_intf_config(interfaces, new_voice_vlan)

            os.makedirs(CONFIG_DIR, exist_ok=True)
            output_file = os.path.join(CONFIG_DIR, f"{hostname}_new_voice_vlan.txt")
            with open(output_file, "w") as f:
                f.write(intf_config_text)

            print(f"Config saved to {output_file}")

        except Exception as e:
            print(f"Error connecting to {host_ip}: {e}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n{e}")
    input("\nPress Enter to exit...")