import requests
import markdown
from bs4 import BeautifulSoup
from lxml import etree as ET
from lxml.etree import CDATA
from email.utils import formatdate
from time import mktime
from datetime import datetime, timedelta

def format_rfc2822(datetime_str):
    dt = datetime.fromisoformat(datetime_str.rstrip('Z'))  # Remove Z if present
    timestamp = mktime(dt.timetuple())
    return formatdate(timestamp, localtime=False, usegmt=True)

def get_commits_with_keyword(repo, keyword, days=1):
    since_date = datetime.now() - timedelta(days=days)
    since = since_date.isoformat()

    commits = []
    page = 1
    while True:
        url = f"https://api.github.com/repos/{repo}/commits?since={since}&page={page}&per_page=100"
        headers = {"Authorization": "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"}
        response = requests.get(url, headers=headers)
        if response.status_code != 200 or not response.json():
            print("response error")
            break

        for commit_data in response.json():
            commit_message = commit_data['commit']['message']
            if keyword.lower() in commit_message.lower():
                commit_info = {
                    'title': commit_message.split("\n")[0],
                    'url': commit_data['html_url'],
                    'message': commit_message,
                    'date': format_rfc2822(commit_data['commit']['committer']['date'])
                }
                commits.append(commit_info)

        page += 1
    return commits

def replace_br_with_p(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    # 查找所有包含<br>的<p>标签
    for p_tag in soup.find_all('p'):
        br_tags = p_tag.find_all('br')
        for br in br_tags:
            br.replace_with(soup.new_tag('p'))
    # 把原来的<p>标签分割成多个<p>标签，每个<br>现在都是新的<p>
    new_html = str(soup)
    return new_html


def append_to_rss_feed(commits, feed_path='feed.xml'):
    try:
        tree = ET.parse(feed_path)
        root = tree.getroot()
    except (ET.ParseError, FileNotFoundError, OSError):
        root = ET.Element('rss', version='2.0')
        channel = ET.SubElement(root, 'channel')
        tree = ET.ElementTree(root)

        title = ET.SubElement(channel, 'title')
        title.text = 'GitHub Commits Feed'
        link = ET.SubElement(channel, 'link')
        link.text = 'https://github.com/username/repo/commits'  # Update with actual repo URL
        description = ET.SubElement(channel, 'description')
        description.text = 'Recent commits from GitHub repo'

    for commit in commits:
        item = ET.Element('item')
        title = ET.SubElement(item, 'title')
        title.text = commit['title']
        link = ET.SubElement(item, 'link')
        link.text = commit['url']

        description = ET.SubElement(item, 'description')
        commit_message_html = markdown.markdown(commit['message'], extensions=['nl2br'])
        commit_message_html = commit_message_html.replace('<br />', '<br>')
        commit_message_html = replace_br_with_p(commit_message_html)
        description.text = CDATA(commit_message_html)

        pubDate = ET.SubElement(item, 'pubDate')
        pubDate.text = commit['date']

        guid = ET.SubElement(item, 'guid')
        guid.text = commit['url']  # 使用commit的URL作为guid
        guid.set('isPermaLink', 'true')  # 如果guid是URL，将isPermaLink设置为"true"

        channel.append(item)

    tree.write(feed_path, pretty_print=True, xml_declaration=True, encoding='UTF-8')


# 设置仓库和关键词
repo = "pytorch/pytorch"
keyword = "inductor"

# 获取commits并更新RSS feed
commits = get_commits_with_keyword(repo, keyword)
if commits:
    append_to_rss_feed(commits)
