import sqlite3
import re
import json
import os

db = sqlite3.connect("../data/zeroblog.db")
db.row_factory = sqlite3.Row
c = db.cursor()

query = """
    SELECT
        post.*, COUNT(comment_id) AS comments, MAX(comment.date_added) AS last_comment,
        (SELECT COUNT(*) FROM post_vote WHERE post_vote.post_id = post.post_id) AS votes
    FROM post
    LEFT JOIN comment USING (post_id)
    WHERE date_published < date('now','-30 day')
    GROUP BY post_id
    HAVING comments = 0 AND votes < 2
    ORDER BY date_published
    LIMIT 100
"""
deleted = 0
data = json.load(open("../data/data.json", "rb"))
print "Posts:", len(data["post"])
for row in c.execute(query):
    deleted += 1
    mp4_file = re.match('.*?src="(.*?)"', row["body"]).group(1)
    data["post"] = filter(lambda post: post["post_id"] != row["post_id"], data["post"])
    print u"Deleting %s / %s" % (row["source"], repr(row["title"])), mp4_file
    os.unlink("../" + mp4_file)

print "Deleted:", deleted,
print "Posts:", len(data["post"])
json.dump(data, open("../data/data.json-new", "wb"), indent=1, sort_keys=True)
