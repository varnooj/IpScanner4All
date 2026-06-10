import subprocess
import platform
import ipaddress
import concurrent.futures
import sys
import os  # <-- برای خروج آنی اضافه شد
from functools import partial

def ping_ip(ip, ping_count):
    if platform.system().lower() == 'windows':
        command = ['ping', '-n', str(ping_count), '-w', '1000', str(ip)]
    else:
        command = ['ping', '-c', str(ping_count), '-W', '1', str(ip)]
    
    try:
        output = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW if platform.system().lower() == 'windows' else 0)
        if output.returncode == 0:
            return str(ip), True
        else:
            return str(ip), False
    except Exception:
        return str(ip), False

def main():
    if len(sys.argv) < 2:
        print("[-] Error: Please provide the input file.")
        print("[*] Example: python scanner.py ips.txt")
        return

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) >= 3 else 'active_ips.txt'

    try:
        with open(input_file, 'r') as f:
            lines = f.readlines()
    except FileNotFoundError:
        print(f"[-] Error: File '{input_file}' not found!")
        return

    ping_input = input("[?] Enter number of pings per IP (default: 4): ").strip()
    
    if ping_input.isdigit() and int(ping_input) > 0:
        ping_count = int(ping_input)
    else:
        print("[!] Invalid input or empty. Defaulting to 4 pings.")
        ping_count = 4

    all_ips = []
    print(f"[*] Extracting IPs from '{input_file}'...")
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            net = ipaddress.ip_network(line, strict=False)
            if net.prefixlen >= 31:
                all_ips.extend([str(ip) for ip in net])
            else:
                all_ips.extend([str(ip) for ip in net.hosts()])
        except ValueError:
            print(f"[-] Invalid format ignored: {line}")

    all_ips = list(set(all_ips))
    total_ips = len(all_ips)
    
    if total_ips == 0:
        print("[-] No valid IPs found to scan.")
        return
        
    print(f"[+] Total IPs to scan: {total_ips}")
    print(f"[*] Ping count set to: {ping_count}\n")
    
    ping_func = partial(ping_ip, ping_count=ping_count)
    active_count = 0
    
    print("[*] Scanning... (Press Ctrl+C to stop instantly)")
    
    try:
        # فایل رو اول خالی می‌کنیم تا نتایج قبلی پاک بشه (اگر می‌خوای به قبلی‌ها اضافه بشه این رو حذف کن)
        open(output_file, 'w').close()
        
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=50)
        futures = [executor.submit(ping_func, ip) for ip in all_ips]
        
        # فایل رو در حالت a (افزودن) باز می‌کنیم
        with open(output_file, 'a') as f:
            for future in concurrent.futures.as_completed(futures):
                ip, is_active = future.result()
                if is_active:
                    print(f"[+] {ip} is UP")
                    f.write(f"{ip}\n")
                    f.flush()  # <--- این دستور فایل رو در همون لحظه روی هارد ذخیره می‌کنه
                    os.fsync(f.fileno()) # اطمینان ۱۰۰٪ از نوشته شدن رو دیسک
                    active_count += 1
                    
        print("-" * 40)
        print(f"[+] Done! {active_count} active IPs saved to '{output_file}'.")

    except KeyboardInterrupt:
        # خروج وحشیانه و بدون درنگ! 
        print(f"\n[!] Exited by user. {active_count} active IPs successfully saved to '{output_file}'.")
        os._exit(0)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n[!] Exited by user.")
        os._exit(0)