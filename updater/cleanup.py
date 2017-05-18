import sqlite3
import re
import json
import os
import time

db = sqlite3.connect("../data/zeroblog.db")
db.row_factory = sqlite3.Row
c = db.cursor()

query = """
    SELECT
        post.*, COUNT(comment_id) AS comments, MAX(comment.date_added) AS last_comment,
        (SELECT COUNT(*) FROM post_vote WHERE post_vote.post_id = post.post_id) AS votes
    FROM post
    LEFT JOIN comment USING (post_id)
    WHERE date_published < strftime('%s', 'now','-20 day')
    GROUP BY post_id
    HAVING comments = 0 AND votes < 4
    ORDER BY date_published
    LIMIT 500
"""
deleted = 0
data = json.load(open("../data/data.json", "rb"))
print "Posts:", len(data["post"])
for row in c.execute(query):
    days = float(time.time() - row["date_published"]) / (60*60*24)
    if days < 20:
        print "! Skipping, days: %.3f" % days
        continue
    deleted += 1
    mp4_file = re.match('.*?src="(.*?)"', row["body"]).group(1)
    data["post"] = filter(lambda post: post["post_id"] != row["post_id"], data["post"])
    print u"Deleting %s / %s" % (row["source"], repr(row["title"])), mp4_file, round(days, 2)
    try:
        os.unlink("../" + mp4_file)
    except Exception, err:
        print "Error deleting: %s" % err
        raw_input("Continue?")

print "Deleted:", deleted,
print "Posts:", len(data["post"])
json.dump(data, open("../data/data.json-new", "wb"), indent=1, sort_keys=True)
