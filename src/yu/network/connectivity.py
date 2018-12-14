import socket
import subprocess
import requests

GLOBAL_WORKING_EXTERNAL_PROXY = None


class _ConnectivityStatus(object):
    def __init__(self):
        self.can_access_external_ip = False

        self.dns_list = []
        self.working_dns = None
        self.can_name_resolve_address = False

        self.can_access_external_url = False

    def __str__(self):
        return_str = "DNS servers configured in /etc/resolv.conf:\n"
        for dns in self.dns_list:
            return_str += " " + (str(dns) + "\n")

        if self.working_dns is None:
            return_str += "No working DNS found\n\n"
        else:
            return_str += "The DNS that will be used for name resolution is " + str(self.working_dns) + "\n\n"

        if self.can_access_external_ip:
            return_str += "Can access external IP addresses\n"
        else:
            return_str += "Can't access external IP addresses\n"

        if self.can_access_external_url:
            return_str += "Can access external URLs\n"
        else:
            return_str += "Can't access external URLs\n"

        return return_str


def can_name_resolve_address(address_to_check):
    """
    Check whether a DNS lookup is successful for the given address

    :param address_to_check: the address to attempt to do a DNS lookup for
    :return: True is DNS lookup was successful; False otherwise
    """
    try:
        subprocess.check_output(['dig', "+time=3", "+retry=2", address_to_check])
        return True
    except:
        return False


def can_name_resolve_external_address(address_to_check='google.com'):
    """
    Check whether we can do a dns lookup on an external address

    :return:  True is DNS lookup was successful; False otherwise
    """
    return can_name_resolve_address(address_to_check)


def get_configured_dns_servers():
    """
    Return a list of the nameservers configured in /etc/resolv.conf

    :return: the list of the nameservers configured in /etc/resolv.conf
    """
    configured_dns_list = []
    with open("/etc/resolv.conf", 'r') as f:
        for line in f:
            if line.startswith('nameserver'):
                configured_dns_list.append(line.strip().split(" ")[1])
    return configured_dns_list


def check_ping(host):
    """
    Check whether or not the provided host can be pinged

    :param host: the host to check
    :return: True if the host could be pinged or False otherwise.
    """
    try:
        subprocess.check_output(['ping', host, '-i', '0.5', '-c', '5', '-w', '5'])
        return True
    except:
        return False


def check_ping_list(host_list_to_check):
    """
    Check whether or not the provided hosts can be pinged

    :param host_list_to_check: A list of hosts to check
    :return: a dictionary of results for each host where the key will be the host and the value will
             be True if it could be pinged or False otherwise. dict[host] = True/False
    """
    results = {}
    for host in host_list_to_check:
        results[host] = check_ping(host)
    return results


def can_access_web_address(address="http://www.google.com", proxy=None):
    """
    Check if we can access the provided address by sending a HTTP GET request

    :param address the web address to check (optional)
            by default this is http://www.google.com
    :param proxy the proxy to use when making the check (optional)
    :return: True is we can; False otherwise
    """
    try:
        proxy_dict = dict()
        if proxy is not None:
            proxy_dict['http'] = proxy
            proxy_dict['https'] = proxy

        r = requests.get(address, proxies=proxy_dict)
        if not r.ok:
            r.raise_for_status()

        return True
    except requests.HTTPError:
        return False


def can_reach_external_ip():
    """
    Check if we can get to the google dns server via ip
    Host: 8.8.8.8 (google-public-dns-a.google.com)
    OpenPort: 53/tcp
    Service: domain (DNS/TCP)

    :return: True is we can; False otherwise
    """
    try:
        socket.setdefaulttimeout(3)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("8.8.8.8", 53))
        return True
    except Exception as ex:
        return False


def check_connectivity():
    """
    Get the connectivity status of the node and populate the values it within a
    yu.network.connectivity.ConnectivityStatus object.

    Gets the configured DNS clients from /etc/resolv.conf and checks whether they are accessible and whether name
    resolution using them is possible for external urls.
    The first dns in the configured list that successfully name resolves an external address will be set as the
    working_external_dns. If none were successful then working_external_dns will be set
    to None.

    :return: yu.network.connectivity.ConnectivityStatus object with the status
    """
    status = _ConnectivityStatus()
    status.can_access_external_ip = can_reach_external_ip()

    status.dns_list = get_configured_dns_servers()
    for dns in status.dns_list:
        if check_ping(dns) is True:
            if can_name_resolve_external_address() is True and status.working_dns is None:
                status.working_dns = dns
                status.can_name_resolve_address = True
                break

    if status.working_dns is False:
        return status

    status.can_access_external_url = can_access_web_address()
    return status
