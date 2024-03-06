import os
import requests
import markdown
from bs4 import BeautifulSoup
from lxml import etree as ET
from lxml.etree import CDATA
from email.utils import formatdate
from time import mktime
from datetime import datetime, timedelta

from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

def requests_retry_session(retries=3, backoff_factor=0.3, status_forcelist=(500, 502, 504, 408), session=None):
    session = session or requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

def format_rfc2822(datetime_str):
    dt = datetime.fromisoformat(datetime_str.rstrip('Z'))
    timestamp = mktime(dt.timetuple())
    return formatdate(timestamp, localtime=False, usegmt=True)

def get_issues_with_keyword(repo, keywords=["inductor", "compile"], days=1, state='open'):
    #import ipdb; ipdb.set_trace()
    since_date = datetime.now() - timedelta(days=days)
    since = since_date.isoformat()
    issues = []
    page = 1
    token = os.getenv("GITHUB_PAT")  # 使用环境变量获取PAT
    headers = {"Authorization": f"token {token}"}
    while True:
        url = f"https://api.github.com/repos/{repo}/issues?state={state}&since={since}&page={page}&per_page=5"
        response = requests_retry_session().get(url, headers=headers, timeout=1000)
        if response.status_code != 200 or not response.json():
            print(f"Response error: {response.status_code}")
            break
        data = response.json()
        if not data:
            break  # 如果没有更多数据，则退出循环
        for issue in data:
            #if 'pull_request' in issue:
            #    continue  # 跳过PR，因为PR也被视作Issue
            issue_title = issue['title']
            if any(keyword.lower() in issue_title.lower() for keyword in keywords):
                #print(issue)
                issue_info = {
                    'title': issue_title,
                    'url': issue['html_url'],
                    'body': issue['body'],
                    'date': format_rfc2822(issue['created_at'])
                }
                issues.append(issue_info)
        page += 1
    return issues


def get_commits_with_keyword(repo, keyword, days=1):
    since_date = datetime.now() - timedelta(days=days)
    since = since_date.isoformat()
    commits = []
    page = 1
    token = os.getenv("GITHUB_PAT")  # 使用环境变量获取PAT
    headers = {"Authorization": f"token {token}"}
    print(headers)
    while True:
        url = f"https://api.github.com/repos/{repo}/commits?since={since}&page={page}&per_page=50"
        response = requests_retry_session().get(url, headers=headers, timeout=10)
        if response.status_code != 200 or not response.json():
            print(f"Response error: {response.status_code}")
            print("json:", response.json())
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

def append_to_rss_feed(commits, feed_path='feed.xml'):
    try:
        tree = ET.parse(feed_path)
        root = tree.getroot()
    except (ET.ParseError, FileNotFoundError, OSError):
        root = ET.Element('rss', version='2.0')
        tree = ET.ElementTree(root)

    channel = root.find('channel')
    if channel is None:
        channel = ET.SubElement(root, 'channel')

    # 设置channel的基本信息，如果它们还未设置
    if not channel.find('title'):
        title = ET.SubElement(channel, 'title')
        title.text = 'GitHub Commits Feed'
    if not channel.find('link'):
        link = ET.SubElement(channel, 'link')
        link.text = 'https://github.com/username/repo/commits'
    if not channel.find('description'):
        description = ET.SubElement(channel, 'description')
        description.text = 'Recent commits from GitHub repo'

    # 创建新items的列表
    new_items = []

    for commit in commits:
        item = ET.Element('item')
        title = ET.SubElement(item, 'title')
        title.text = commit['title']
        link = ET.SubElement(item, 'link')
        link.text = commit['url']

        description = ET.SubElement(item, 'description')
        commit_message_html = markdown.markdown(commit['message'], extensions=['nl2br'])
        description.text = CDATA(commit_message_html)

        pubDate = ET.SubElement(item, 'pubDate')
        pubDate.text = commit['date']

        guid = ET.SubElement(item, 'guid', isPermaLink="true")
        guid.text = commit['url']

        # 将新item添加到列表
        new_items.append(item)

    # 获取现有items
    existing_items = list(channel.findall('item'))

    # 移除channel中所有现有的item
    for item in existing_items:
        channel.remove(item)

    # 将新items和现有items合并，确保新items在前
    all_items = new_items + existing_items

    # 将合并后的items添加回channel
    for item in all_items:
        channel.append(item)

    tree.write(feed_path, pretty_print=True, xml_declaration=True, encoding='UTF-8')

def append_issues_to_rss_feed(issues, feed_path='feed_issues.xml'):
    try:
        tree = ET.parse(feed_path)
        root = tree.getroot()
    except (ET.ParseError, FileNotFoundError, OSError):
        root = ET.Element('rss', version='2.0')
        tree = ET.ElementTree(root)

    channel = root.find('channel')
    if channel is None:
        channel = ET.SubElement(root, 'channel')

    # 设置channel的基本信息，如果它们还未设置
    if not channel.find('title'):
        title = ET.SubElement(channel, 'title')
        title.text = 'GitHub issues Feed'
    if not channel.find('link'):
        link = ET.SubElement(channel, 'link')
        link.text = 'https://github.com/username/repo/issues'
    if not channel.find('description'):
        description = ET.SubElement(channel, 'description')
        description.text = 'Recent issues from GitHub repo'

    # 创建新items的列表
    new_items = []

    for issue in issues:
        item = ET.Element('item')
        title = ET.SubElement(item, 'title')
        title.text = issue['title']
        link = ET.SubElement(item, 'link')
        link.text = issue['url']

        body = ET.SubElement(item, 'description')
        commit_message_html = markdown.markdown(issue['body'], extensions=['nl2br'])
        body.text = CDATA(commit_message_html)

        pubDate = ET.SubElement(item, 'pubDate')
        pubDate.text = issue['date']

        guid = ET.SubElement(item, 'guid', isPermaLink="true")
        guid.text = issue['url']

        # 将新item添加到列表
        new_items.append(item)

    # 获取现有items
    existing_items = list(channel.findall('item'))

    # 移除channel中所有现有的item
    for item in existing_items:
        channel.remove(item)

    # 将新items和现有items合并，确保新items在前
    all_items = new_items + existing_items

    # 将合并后的items添加回channel
    for item in all_items:
        channel.append(item)

    tree.write(feed_path, pretty_print=True, xml_declaration=True, encoding='UTF-8')


# 设置仓库和关键词
repo = "pytorch/pytorch"
keyword = "inductor"

# 获取commits并更新RSS feed
#commits = get_commits_with_keyword(repo, keyword)
issues = get_issues_with_keyword(repo)
if issues:
    #print(f"Appending {len(commits)} new commits to the feed.")
    print(f"Appending {len(issues)} new issues to the feed.")
    append_issues_to_rss_feed(issues)
    #append_to_rss_feed(commits, "inductor_feeds.xml")
