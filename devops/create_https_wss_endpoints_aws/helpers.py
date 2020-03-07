
import subprocess




def shcmd2(cmd, ignore_error=False):
    """ customized version of shcmd created by aw """
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True)
    output = proc.stdout.read()
    output_string = output.decode("utf-8")
    return output_string


def retrieve_instance_region(ip):
    """ deduce instance region from its ipv4 """
    cmd = "host {ip}".format(ip=ip)
    resp = shcmd2(cmd)
    info = resp.split('.')
    if info[-4] ==  'compute':
        region = info[-5]
    elif info[-4] == 'compute-1':
        region = 'us-east-1'
    else:
        raise ValueError("cannot deduce region from name {}".format(info))
    return region


def verify_nodes_same_region(array_ip):
    reg = retrieve_instance_region(array_ip[0])
    for ip in array_ip:
        if retrieve_instance_region(ip) != reg:
            sys.exit()
