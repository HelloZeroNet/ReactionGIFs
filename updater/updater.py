import urllib2
import re
import os
import json
import time
import subprocess
import sys

opener = urllib2.build_opener()
opener.addheaders = [('User-agent', 'Mozilla/5.0 (Windows NT 6.3; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/48.0.2564.41 Safari/537.36')]

class Updater:
    def __init__(self):
        pass

    def getVideos(self, pages=1):
        videos = []
        for page in range(pages):
            videos += self.getPage(page)
        return videos


class Devopreactions(Updater):
    def getPage(self, page=0):
        print "- Getting Devopreactions page %s..." % page
        data = opener.open("http://devopsreactions.tumblr.com/page/%s" % page).read()
        open("temp/devopsreactions.html", "w").write(data)
        # data = open(".temp/devopsreactions.html").read()
        videos = []
        for part in data.split('item_content'):
            match = re.match(""".*?post_title.*?href.*?>(?P<title>.*?)</a>.*?src=["'](?P<gif_url>.*?gif)["']""", part, re.DOTALL)
            if match:
                video = match.groupdict()
                video["source"] = "DevopsReactions"
                videos.append(video)
        return videos


class RedditGifs(Updater):
    def getPage(self, page=0):
        if page > 0: return []
        print "- Getting RedditGifs page %s..." % page
        data = json.load(opener.open("https://www.reddit.com/r/gifs/hot.json"))
        videos = []
        for row in data["data"]["children"]:
            if not row: continue
            if "reddit.com/" in row["data"]["url"]: continue

            if row["data"]["score"] > 4000:
                video = {"title": row["data"]["title"], "source": "RedditGifs"}
                url = row["data"]["url"]
                if url.endswith(".mp4"):
                    video["gif_url"] = url
                elif url.endswith(".gifv"):
                    video["gif_url"] = url.replace(".gifv", ".mp4")
                elif url.endswith(".gif") and "imgur.com" in url:
                    video["gif_url"] = url.replace(".gif", ".mp4")
                elif "gfycat.com" in url and not url.endswith(".mp4"):
                    video["gif_url"] = url.replace("www.gfycat.com", "zippy.gfycat.com")+".mp4"
                else:
                    video["gif_url"] = url
                videos.append(video)
        return videos


class RedditNsfwGifs(Updater):
    def getPage(self, page=0):
        if page > 0: return []
        print "- Getting RedditNsfwGifs page %s..." % page
        data = json.load(opener.open("https://www.reddit.com/r/nsfw_gifs/hot.json"))
        videos = []
        for row in data["data"]["children"]:
            if not row: continue
            if "reddit.com/" in row["data"]["url"]: continue

            if row["data"]["score"] > 200:
                video = {"title": row["data"]["title"], "source": "RedditNsfwGifs"}
                url = row["data"]["url"]
                if url.endswith(".mp4"):
                    video["gif_url"] = url
                elif url.endswith(".gifv"):
                    video["gif_url"] = url.replace(".gifv", ".mp4")
                elif url.endswith(".gif") and "imgur.com" in url:
                    video["gif_url"] = url.replace(".gif", ".mp4")
                else:
                    video["gif_url"] = url
                videos.append(video)
        return videos


def download(gif_url, gif_path):
    req = urllib2.Request(gif_url)
    req.add_header("Referer", gif_url)
    data = urllib2.urlopen(req).read()
    if "<html" in data:
        new_url = re.search("(http[s]{0,1}://[^\"\']*?mp4)[\"']", data).group(1)
        print "- Html source, redirecting to %s" % new_url
        req = urllib2.Request(new_url)
        req.add_header("Referer", new_url)
        data = urllib2.urlopen(new_url).read()

    open(gif_path, "wb").write(data)
    return gif_path


def convertToMp4(gif_path, mp4_path):
    if os.path.isfile(mp4_path):
        os.unlink(mp4_path)
    cmd = [
        "ffmpeg/bin/ffmpeg",
        "-i", gif_path,
        "-c:v", "libx264",
        "-crf", "28",
        "-pix_fmt", "yuv420p",
        "-movflags", "faststart",
        "-force_key_frames", "00:00:00.100",
        "-filter:v", "scale=trunc(iw/2)*2:trunc(ih/2)*2",
        "-vf", "scale=floor(iw*min(1\,if(gt(iw\,ih)\,600/iw\,(500*sar)/ih))/2)*2:(floor((ow/dar)/2))*2",
        mp4_path
    ]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output = process.stderr.read()
    size_match = re.search("Video: h264.*, ([0-9]+)x([0-9]+)", output)
    if size_match:
        return size_match.groups()
    else:
        print output
        return False


def getMp4Dimensions(mp4_path):
    raise "Unsupported yet"


def updateSites():
    added = 0
    data = json.load(open("../data/data.json"))
    titles = [post["title"] for post in data["post"]]

    sites = [RedditGifs(), Devopreactions(), RedditNsfwGifs()]
    videos = []
    for site in sites:
        videos += site.getVideos(pages=3)

    source_added = {}

    for video in reversed(videos):
        if video["source"] in source_added:
            print "! Only one video per section per update"
            continue

        if video["title"] in titles:
            print "* Already exist, skipping: %s / %s" % (video["source"], video["title"])
            continue
        if video.get("mp4_url"):
            raise "Unsupported"
            """print "- Downloading MP4 %s..." % video["mp4_url"]
            mp4_path = download(video["mp4_url"], "temp/last.mp4")
            print "- Getting dimensions of %s..." % mp4_path
            video_size = getMp4Dimensions(mp4_path)"""
        else:
            print "- Downloading GIF %s..." % video["gif_url"]
            try:
                gif_path = download(video["gif_url"], "temp/last.gif")
            except Exception, err:
                print "Error downloading video: %s, skipping" % err
                continue
            mp4_path = "../data/mp4-%s/%s.mp4" % (video["source"].lower(), data["next_post_id"])
            print "- Converting %s to %s..." % (gif_path, mp4_path)
            video_size = convertToMp4(gif_path, mp4_path)

        if not os.path.isfile(mp4_path):
            print "! Converting failed, skipping"
            continue

        if os.path.getsize(mp4_path) > 1024*1024 or os.path.getsize(mp4_path) < 30:
            print "! Too large or too small, skipping: %s" % os.path.getsize(mp4_path)
            os.unlink(mp4_path)
            continue

        if video_size:
            # 90 158
            print "- Adding to data.json..."
            width, height = map(float, video_size)
            width_resized = 600
            height_resized = round(height * (600.0 / width))
            if height_resized > 500:
                height_resized = 500
                width_resized = round(width * (500.0 / height))

            post = {
                "post_id": data["next_post_id"],
                "title": video["title"],
                "date_published": time.time(),
                "source": video["source"],
                "body":
                    '<video src="data/mp4-%s/%s.mp4" width=%.0f height=%.0f loop muted preload="auto"></video>' %
                    (video["source"].lower(), data["next_post_id"], width_resized, height_resized)
            }
            data["post"].insert(0, post)
            data["next_post_id"] += 1
            json.dump(data, open("../data/data.json", "w"), indent=1)
            titles.append(video["title"])

            source_added[video["source"]] = True
            added += 1
        else:
            print "! Error converting gif to mp4"
            continue
    return added

if __name__ == "__main__":
    added = updateSites()
    if added:
        os.chdir(sys.argv[1])
        os.system("python zeronet.py siteSign 1Gif7PqWTzVWDQ42Mo7np3zXmGAo3DXc7h --publish")
    print "Done, added: %s" % added
    #download("http://imgur.com/CDWxtM7", "temp/last.gif")
    #print convertToMp4("temp/last.gif", "temp/last.mp4")
