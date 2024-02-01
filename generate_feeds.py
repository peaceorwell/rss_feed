import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

def get_commits_with_keyword(repo, keyword, days=1):
    since_date = datetime.now() - timedelta(days=days)
    since = since_date.isoformat()

    commits = []
    page = 1
    while True:
        url = f"https://api.github.com/repos/{repo}/commits?since={since}&page={page}&per_page=100"
        response = requests.get(url)
        if response.status_code != 200 or not response.json():
            break

        for commit_data in response.json():
            commit_message = commit_data['commit']['message']
            if keyword.lower() in commit_message.lower():
                commit_info = {
                    'title': commit_message.split("\n")[0],
                    'url': commit_data['html_url'],
                    'message': commit_message,
                    'date': commit_data['commit']['committer']['date']
                }
                commits.append(commit_info)

        page += 1
    return commits

def append_to_rss_feed(commits, feed_path='feed.xml'):
    try:
        tree = ET.parse(feed_path)
        root = tree.getroot()
    except (ET.ParseError, FileNotFoundError):
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
        description.text = (
            f"<p><b>Commit Message:</b> {commit['message']}</p>"
            f"<p><a href='{commit['url']}'>View Commit on GitHub</a></p>"
        )
        pubDate = ET.SubElement(item, 'pubDate')
        pubDate.text = commit['date']

        root.append(item)

    tree.write(feed_path, encoding='utf-8', xml_declaration=True)

# 设置仓库和关键词
repo = "pytorch/pytorch"
keyword = "inductor"

# 获取commits并更新RSS feed
commits = get_commits_with_keyword(repo, keyword)
if commits:
    append_to_rss_feed(commits)
