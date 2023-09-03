import os
from tqdm import tqdm
import json
import requests
from multiprocessing import Pool


requests.adapters.DEFAULT_RETRIES = 5

def crawl(ip, domain):
    url = "http://"+ip

    headers = {
        "Host": domain,
        'Connection': 'close',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537',
    }

    response = requests.get(url, headers=headers, timeout=10)
    return response

def crawl_only_one(ip):
    url = "http://"+ip
    headers = {
        'Connection': 'close',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537',
    }
    response = requests.get(url, headers=headers, timeout=10)
    return response

# 爬取单个http请求
def crawl_single_http(ip='None', domain='None'):
    try:
        if ip != 'None' and domain != 'None':
            response = crawl(ip=ip, domain=domain)
        elif ip == 'None':
            response = crawl_only_one(domain)
        elif domain == 'None':
            response = crawl_only_one(ip)
        else:
            raise Exception
        
        response.encoding = response.apparent_encoding
        text = response.text
        if response.status_code == 200:
            status = 1
        else:
            status = 0
        return text, status
    except Exception as e:
        return  str(e), 0
    

import dns
from dns.resolver import Resolver
from dns.exception import Timeout

resolver = Resolver()
resolver.timeout = 5.0
resolver.lifetime = 10.0

def resolve_domains(server_ip, domain):
    resolver.nameservers = [server_ip]

    try:
        answer = resolver.resolve(domain, "A")  # 使用"A"来查询IPv4地址，因为解析结果中没有IPv6地址

        # 一个域名可能有多个IP地址，所以这里获取所有返回的IP地址
        with open(os.path.join(dns_res_folder, f'{server_ip}_{domain}_1.txt'), 'w', encoding='utf-8') as f:
            print(server_ip + '_' + domain + ':' + '|'.join([rdata.address for rdata in answer]))
            f.write('\n'.join([rdata.address for rdata in answer]))
            return [rdata.address for rdata in answer]
        
    except dns.resolver.NoAnswer:
        with open(os.path.join(dns_res_folder, f'{server_ip}_{domain}_0.txt'), 'w', encoding='utf-8') as f:
            print(f"No answer for {domain} from {server_ip}\n")
            f.write("No answer")
    except dns.resolver.NXDOMAIN:
        with open(os.path.join(dns_res_folder, f'{server_ip}_{domain}_0.txt'), 'w', encoding='utf-8') as f:
            print(f"Domain {domain} does not exist from {server_ip}\n")
            f.write("Domain does not exist")
    except Timeout:
        with open(os.path.join(dns_res_folder, f'{server_ip}_{domain}_0.txt'), 'w', encoding='utf-8') as f:
            print(f"Domain {domain} timeout from {server_ip}\n")
            f.write("Timeout")
    except dns.resolver.NoNameservers:
        with open(os.path.join(dns_res_folder, f'{server_ip}_{domain}_0.txt'), 'w', encoding='utf-8') as f:
            print(f"No nameservers could answer the query for {domain} from {server_ip}\n")
            f.write("NoNameservers")
    except Exception as e:
        with open(os.path.join(dns_res_folder, f'{server_ip}_{domain}_0.txt'), 'w', encoding='utf-8') as f:
            print(e)
            f.write('error')
    
    return None

def query_dns_and_http(server_ip, domain):
    rdatas = resolve_domains(server_ip, domain)
    text, status = crawl_single_http(domain)
    with open(os.path.join(http_res_folder, f'{server_ip}_{domain}_None_{status}.txt'), 'w', encoding='utf-8') as f:
        f.write(text)
    if rdatas:
        for ip in rdatas:
            text, status = crawl_single_http(ip, domain)
            with open(os.path.join(http_res_folder, f'{server_ip}_{domain}_{ip}_{status}.txt'), 'w', encoding='utf-8') as f:
                f.write(text)
            text, status = crawl_single_http(ip)
            with open(os.path.join(http_res_folder, f'{server_ip}_None_{ip}_{status}.txt'), 'w', encoding='utf-8') as f:
                f.write(text)
            print(f'{server_ip}\t{ip}\t{domain}\t crawl finished!')
    else:
        with open(os.path.join(http_res_folder, f'{server_ip}_{domain}_None_None.txt'), 'w', encoding='utf-8') as f:
            f.write('')

def get_my_ip():
    headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Trident/7.0; rv:11.0) like Gecko',"Content-Type": "application/json"
                }
    text_ = requests.get("http://ip-api.com/json/", headers=headers, timeout=5)
    print(json.loads(text_.content))
    return json.loads(text_.content)


from concurrent.futures import ThreadPoolExecutor

def worker(args):
    server, domain = args
    query_dns_and_http(server, domain)


import paramiko
from scp import SCPClient
def upload_file(host, port, username, password, local_file_path, remote_file_path):
            # 创建 SSH 客户端
            ssh = paramiko.SSHClient()
            # 自动添加目标服务器（远程主机）的 SSH 密钥
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            # 连接 SSH 服务器
            ssh.connect(host, port=port, username=username, password=password)
            
            # 使用 SCP 协议上传文件
            with SCPClient(ssh.get_transport()) as scp:
                scp.put(local_file_path, remote_file_path)
            
            ssh.close()

import tarfile
import os

def compress_folder(input_folder, output_filename):
    with tarfile.open(output_filename, "w:gz") as tar:
        tar.add(input_folder, arcname=os.path.basename(input_folder))


if __name__ == "__main__":
    
    if not os.path.exists('/home/res'):
        os.mkdir('/home/res')

    my_ip_info = get_my_ip()

    
    if 'query' in my_ip_info:
        my_ip = my_ip_info['query']
        res_folder = os.path.join('/home/res/', my_ip)
        os.mkdir(res_folder)

        with open(os.path.join(res_folder, f'ip_info_{my_ip}.txt'), 'w') as f:
            f.write(json.dumps(my_ip_info))
            
        dns_res_folder = os.path.join(res_folder, 'dns_res')
        os.mkdir(dns_res_folder)

        http_res_folder = os.path.join(res_folder, 'http_res')
        os.mkdir(http_res_folder)

        all_request = []
        for server in ['116.62.199.66', '116.62.26.7', '121.43.225.68', '47.99.55.5', '139.196.183.60']:
            with open(f'/home/qname_list/qname_{server}.txt', 'r') as f:
                s = f.read().strip('\n').split('\n')
            for domain in s:
                all_request.append((server, domain))
        print('load request list finished!')
        
        # 设置线程池大小（例如10），您可以根据需要调整
        with ThreadPoolExecutor(max_workers=100) as executor:
            list(tqdm(executor.map(worker, all_request), total=len(all_request)))


        # ===========================================================上传文件

        local_file_path = f'/home/res/{my_ip}'
        compressed_filename = f"/home/{my_ip}.tar.gz"

        compress_folder(local_file_path, compressed_filename)

        # 使用函数上传文件
        host = '47.243.138.97'
        port = 22  # 默认的 SSH 端口是22
        username = 'daidingzhang'
        password = '123456'
        remote_file_path = f'/home/daidingzhang/{my_ip}.tar.gz'

        upload_file(host, port, username, password, compressed_filename, remote_file_path)
