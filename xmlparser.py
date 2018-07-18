from bs4 import BeautifulSoup

# 解析xml
def parse(xml):
    ticket_dict = {}
    soup = BeautifulSoup(xml, "lxml").find(name="error")
    for item in soup.find_all(recursive=False):
        ticket_dict[item.name] = item.text
    return ticket_dict
