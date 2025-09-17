import dns.message
import dns.name
import dns.query
import dns.rdatatype
import sys

# IP address of one of the 13 root DNS servers (a.root-servers.net)
ROOT_SERVER_IP = "198.41.0.4"


def resolve(hostname: str, record_type: str = "A") -> str:
    """
    Recursively resolves a hostname to an IP address.
    """
    domain = dns.name.from_text(hostname)
    nameservers = [ROOT_SERVER_IP]

    while nameservers:
        ns_ip = nameservers.pop(0)
        print(f"▶ Querying {ns_ip} for {hostname} ({record_type})")

        query = dns.message.make_query(domain, record_type)

        try:
            response = dns.query.udp(query, ns_ip, timeout=2)
        except dns.exception.Timeout:
            print(f"⚠ Timeout querying {ns_ip}. Trying next server.")
            continue

        # --- Step 1: Check the ANSWER section ---
        if response.answer:
            for rrset in response.answer:
                for item in rrset.items:
                    if item.rdtype == dns.rdatatype.from_text(record_type):
                        print(f"✅ Found {record_type} record: {item.to_text()}")
                        return item.to_text()
                    elif item.rdtype == dns.rdatatype.CNAME:
                        cname_target = item.target.to_text()
                        print(f"↪ Found CNAME: {hostname} -> {cname_target}. Following alias.")
                        return resolve(cname_target, record_type)

        # --- Step 2: Check the ADDITIONAL section for glue records ---
        next_hop_ips = []
        if response.additional:
            for rrset in response.additional:
                for item in rrset.items:
                    if item.rdtype == dns.rdatatype.A:
                        next_hop_ips.append(item.address)

        if next_hop_ips:
            nameservers.extend(next_hop_ips)
            continue

        # --- Step 3: Check the AUTHORITY section for NS hostnames ---
        if response.authority:
            for rrset in response.authority:
                for item in rrset.items:
                    if item.rdtype == dns.rdatatype.NS:
                        ns_hostname = item.target.to_text()
                        print(f"ℹ Authority refers to NS: {ns_hostname}. Resolving its IP.")
                        try:
                            ns_ip_to_add = resolve(ns_hostname, "A")
                            nameservers.append(ns_ip_to_add)
                        except RuntimeError as e:
                            print(f"❌ Could not resolve NS {ns_hostname}: {e}")
                        break
                break

    raise RuntimeError(f"Could not resolve {hostname}: No more nameservers to query.")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        target_hostname = sys.argv[1]
    else:
        target_hostname = "www.google.com"

    print(f"--- Resolving: {target_hostname} ---")
    try:
        ip_address = resolve(target_hostname)
        print(f"\n✅ SUCCESS: Final IP for {target_hostname} is {ip_address}")
    except Exception as e:
        print(f"\n❌ FAILED: {e}")
