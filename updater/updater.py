import urllib
import re
import os
import json
import time
import subprocess


class Updater:
    def __init__(self):
        pass

    def getVideos(self, pages=1):
        videos = []
        for page in range(pages):
            videos += self.getPage(page)
        return videos


class Devopreactions(Updater):
    def getPage(self, page=1):
        print "- Getting Devopreactions page %s..." % page
        data = urllib.urlopen("http://devopsreactions.tumblr.com/page/%s" % page).read()
        open("temp/devopsreactions.html", "w").write(data)
        # data = open(".temp/devopsreactions.html").read()
        videos = []
        for part in data.split('item_content'):
            match = re.match(""".*?post_title.*?href.*?>(?P<title>.*?)</a>.*?src=["'](?P<gif_url>.*?gif)["']""", part, re.DOTALL)
            if match:
                videos.append(match.groupdict())
        return videos


def download(gif_url, gif_path):
    open(gif_path, "wb").write(
        urllib.urlopen(gif_url).read()
    )
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
        "-filter:v scale=trunc(iw/2)*2:trunc(ih/2)*2",
        mp4_path
    ]
    process = subprocess.Popen(" ".join(cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output = process.stderr.read()
    size_match = re.search("Video: h264.*, ([0-9]+)x([0-9]+),", output)
    if size_match:
        return size_match.groups()
    else:
        print output
        return False


def updateSites():
    added = 0
    data = json.load(open("../data/data.json"))
    titles = [post["title"] for post in data["post"]]

    sites = [Devopreactions()]
    for site in sites:
        videos = site.getVideos(40)

    for video in reversed(videos):
        if video["title"] in titles:
            print "* Already exist, skipping: %s" % video["title"]
            continue

        print "- Downloading %s..." % video["gif_url"]
        gif_path = download(video["gif_url"], "temp/last.gif")

        mp4_path = "../data/mp4/%s.mp4" % data["next_post_id"]
        print "- Converting %s to %s..." % (gif_path, mp4_path)
        video_size = convertToMp4(gif_path, mp4_path)
        if video_size:
            #90 158
            print "- Adding to data.json..."
            width, height = map(float, video_size)
            width_resized = 600
            height_resized = round(height*(600.0/width))
            if height_resized > 500:
                height_resized = 500
                width_resized = round(width*(500.0/height))

            post = {
                "post_id": data["next_post_id"],
                "title": video["title"],
                "date_published": time.time(),
                "body":
                    '<video src="data/mp4/%s.mp4" width=%.0f height=%.0f loop muted preload="auto" autoplay></video>' %
                    (data["next_post_id"], width_resized, height_resized)
            }
            data["post"].insert(0, post)
            data["next_post_id"] += 1
            json.dump(data, open("../data/data.json", "w"), indent=1)
            titles.append(video["title"])
            added += 1
        else:
            print "! Error converting gif to mp4"
            continue
    return added

if __name__ == "__main__":
    added = updateSites()
    if added:
        os.chdir("../../../")
        os.system("python zeronet.py siteSign 1NgBW8ohapJ2f2dRXThEYrDTYghUzLXgf2")
    print "Done, added: %s" % added
    #print convertToMp4("temp/last.gif", "temp/last.mp4")
