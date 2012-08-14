import os

from google.appengine.ext import db
import webapp2
import jinja2

import database_models
import tools




template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir),
                               autoescape = True)

# Renders parameters into the template
def render_template(template, **params):
    t = jinja_env.get_template(template)
    return t.render(params)

class BlogHandler(webapp2.RequestHandler):
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)

    def render_str(self, template, **params):
        return render_template(template, **params)

    def render(self, template, **kw):
        self.write(self.render_str(template, **kw))

    def set_secure_cookie(self, name, val):
        cookie_val = tools.make_secure_val(val)
        self.response.headers.add_header('Set-Cookie', '%s=%s; Path=/' % (name, cookie_val))

    def read_secure_cookie(self, name):
        cookie_val = self.request.cookies.get(name)
        return cookie_val and tools.check_secure_val(cookie_val)

    def login(self, user):
        self.set_secure_cookie('user_id', str(user.key().id()))

    def logout(self):
        self.response.headers.add_header('Set-Cookie', 'user_id=; Path=/')

    def initialize(self, *a, **kw):
        webapp2.RequestHandler.initialize(self, *a, **kw)
        uid = self.read_secure_cookie('user_id')
        self.user = uid and database_models.User.by_id(int(uid))

def render_post(response, post):
    response.out.write('<b>' + post.subject + '</b><br>')
    response.out.write(post.content)



# Handlers for different blog pages
class Login(BlogHandler):
    def get(self):
        self.render("login.html")

    def post(self):
        self.username = self.request.get('username')
        self.password = self.request.get('password')
        u = database_models.User.login(self.username, self.password)
        if u:
            self.login(u)
            self.redirect('/welcome')
        else:
            self.redirect('/login')


class Logout(BlogHandler):
    def get(self):
        self.logout()
        self.redirect('/')





class Signup(BlogHandler):
    def get(self):
        self.render("signup.html")

    def post(self):
        self.username = self.request.get('username')
        self.password = self.request.get('password')
        self.verify = self.request.get('verify')
        self.email = self.request.get('email')
        params = dict(username = self.username,
            email = self.email)
        we_have_error = False
        if not tools.valid_username(self.username):
            we_have_error = True
            params['error_username'] = "Invalid username!"
        if not tools.valid_password(self.password):
            we_have_error = True
            params['error_password'] = "Invalid password!"
        if not tools.valid_verify(self.password, self.verify):
            we_have_error = True
            params['error_verify'] = "Passwords do not match!"
        #if not tools.valid_email(self.email):
        #    we_have_error = True
        #    params['error_email'] = "Invalid email!"
        if we_have_error:
            self.render("signup.html", **params)
        else:
            #make sure the user doesn't already exist
            u = database_models.User.by_name(self.username)
            if u:
                params['error_username'] = 'That user already exists.'
                self.render('signup.html', **params)
            else:
                u = database_models.User.register(self.username, self.password, self.email)
                u.put()

                self.login(u)
                self.redirect('/welcome')


class Welcome(BlogHandler):
    def get(self):
        if self.user:
            self.render("welcome.html", username=self.user.username)
        else:
            self.redirect('/signup')


class BlogFront(BlogHandler):
    def get(self):
        posts = db.GqlQuery("select * from Post order by created desc limit 10")
        self.render('front.html', posts = posts)

class PostPage(BlogHandler):
    def get(self, post_id):
        key = db.Key.from_path('Post', int(post_id), parent=database_models.blog_key())
        post = db.get(key)

        if not post:
            self.error(404)
            return

        self.render("permalink.html", post = post)

class NewPost(BlogHandler):
    def get(self):
        self.render("newpost.html")

    def post(self):
        subject = self.request.get('subject')
        content = self.request.get('content')

        if subject and content:
            p = database_models.Post(parent = database_models.blog_key(), subject = subject, content = content)
            p.put()
            self.redirect('/%s' % str(p.key().id()))
        else:
            error = "subject and content, please!"
            self.render("newpost.html", subject=subject, content=content, error=error)

app = webapp2.WSGIApplication([('/?', BlogFront),
                                ('/([0-9]+)', PostPage),
                                ('/newpost', NewPost),
                                ('/signup', Signup),
                                ('/login', Login),
                                ('/welcome', Welcome),
                                ('/logout', Logout)
                                ], debug=True)
