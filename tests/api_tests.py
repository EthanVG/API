import unittest
import os
import json
try: from urllib.parse import urlparse
except ImportError: from urlparse import urlparse # Python 2 compatibility

# Configure our app to use the testing databse
os.environ["CONFIG_PATH"] = "posts.config.TestingConfig"

from posts import app
from posts import models
from posts.database import Base, engine, session

class TestAPI(unittest.TestCase):
    """ Tests for the posts API """

    def setUp(self):
        """ Test setup """
        self.client = app.test_client()

        # Set up the tables in the database
        Base.metadata.create_all(engine)

    def tearDown(self):
        """ Test teardown """
        session.close()
        # Remove the tables and their data from the database
        Base.metadata.drop_all(engine)
    
    def test_get_empty_posts(self):
        """ Getting posts from an empty database """
        response = self.client.get("/api/posts",
            headers=[("Accept", "application/json")]
        )
    
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "application/json")
    
        data = json.loads(response.data.decode("ascii"))
        self.assertEqual(data, [])
    
    def test_get_posts(self):
        """ Getting posts from a populated database """
        postA = models.Post(title="Example Post A", body="Just a test")
        postB = models.Post(title="Example Post B", body="Still a test")

        session.add_all([postA, postB])
        session.commit()
        
        response = self.client.get("/api/posts",
            headers=[("Accept", "application/json")]
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "application/json")

        data = json.loads(response.data.decode("ascii"))
        self.assertEqual(len(data), 2)

        postA = data[0]
        self.assertEqual(postA["title"], "Example Post A")
        self.assertEqual(postA["body"], "Just a test")

        postB = data[1]
        self.assertEqual(postB["title"], "Example Post B")
        self.assertEqual(postB["body"], "Still a test")
        
    def test_get_post(self):
        """ Getting a single post from a populated database """
        postA = models.Post(title="Example Post A", body="Just a test")
        postB = models.Post(title="Example Post B", body="Still a test")

        session.add_all([postA, postB])
        session.commit()
    
        response = self.client.get("/api/posts/{}".format(postB.id),
            headers=[("Accept", "application/json")]
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "application/json")

        post = json.loads(response.data.decode("ascii"))
        self.assertEqual(post["title"], "Example Post B")
        self.assertEqual(post["body"], "Still a test")
            
    def test_get_non_existent_post(self):
        """ Getting a single post which doesn't exist """
        response = self.client.get("/api/posts/1",
            headers=[("Accept", "application/json")]
        )
    
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.mimetype, "application/json")
    
        data = json.loads(response.data.decode("ascii"))
        self.assertEqual(data["message"], "Could not find post with id 1")
        
    def test_unsupported_accept_header(self):
        response = self.client.get("/api/posts",
            headers=[("Accept", "application/xml")]
        )

        self.assertEqual(response.status_code, 406)
        self.assertEqual(response.mimetype, "application/json")

        data = json.loads(response.data.decode("ascii"))
        self.assertEqual(data["message"],
                         "Request must accept application/json data")
    
    def test_delete_post(self):
        """ Delete a single post """
        postA = models.Post(title="Example Post A", body="Just a test")
        session.add_all([postA,])
        session.commit()
        
        response = self.client.delete("/api/posts/{}".format(postA.id),
            headers=[("Accept", "application/json")]
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "application/json")
        data = json.loads(response.data.decode("ascii"))
        self.assertEqual(len(data), 0)
        
    def test_get_posts_with_title_and_body(self):
        """ Filtering posts by title """
        postA = models.Post(title="Post with bells", body="Just a test, without whistles")
        postB = models.Post(title="Post with whistles", body="Still a test, without bells")
        postC = models.Post(title="Post with bells and whistles",
                            body="Another test, with bells and whistles")

        session.add_all([postA, postB, postC])
        session.commit()

        response = self.client.get("/api/posts?title_like=whistles&body_like=",
            headers=[("Accept", "application/json")]
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "application/json")

        posts = json.loads(response.data.decode("ascii"))
        self.assertEqual(len(posts), 2)

        post = posts[0]
        self.assertEqual(post["title"], "Post with whistles")
        self.assertEqual(post["body"], "Still a test, without bells")

        post = posts[1]
        self.assertEqual(post["title"], "Post with bells and whistles")
        self.assertEqual(post["body"], "Another test, with bells and whistles")
        
    def test_post_post(self):
        """ Posting a new post """
        data = {
            "title": "Example Post",
            "body": "Just a test"
        }

        response = self.client.post("/api/posts",
            data=json.dumps(data),
            content_type="application/json",
            headers=[("Accept", "application/json")]
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.mimetype, "application/json")
        self.assertEqual(urlparse(response.headers.get("Location")).path,
                         "/api/posts/1")

        data = json.loads(response.data.decode("ascii"))
        self.assertEqual(data["id"], 1)
        self.assertEqual(data["title"], "Example Post")
        self.assertEqual(data["body"], "Just a test")

        posts = session.query(models.Post).all()
        self.assertEqual(len(posts), 1)

        post = posts[0]
        self.assertEqual(post.title, "Example Post")
        self.assertEqual(post.body, "Just a test")    
    
    def test_unsupported_mimetype(self):
        data = "<xml></xml>"
        response = self.client.post("/api/posts",
            data=json.dumps(data),
            content_type="application/xml",
            headers=[("Accept", "application/json")]
        )

        self.assertEqual(response.status_code, 415)
        self.assertEqual(response.mimetype, "application/json")

        data = json.loads(response.data.decode("ascii"))
        self.assertEqual(data["message"],
                         "Request must contain application/json data")

if __name__ == "__main__":
    unittest.main()
