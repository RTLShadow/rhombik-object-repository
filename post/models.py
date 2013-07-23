from django.db import models
from django.contrib import admin
from django.contrib.auth.models import User, Group
from datetime import datetime
import thumbnailer.shadowbox

class Post(models.Model):
    try:
        self.time
    except NameError:
        time = datetime.now()

    title = models.CharField(max_length=60,unique=True)
    thumbnail = models.CharField(max_length=60)
    body = models.TextField()
    created = models.DateTimeField(default=time)
    author = models.ForeignKey(User, related_name='author',default=User) 
    allow_html = models.BooleanField(default=False)
    ##only used internally, don't set
    body_rendered = models.TextField('Entry body as HTML', blank=True, null=True)


    def __unicode__(self):
        return self.title
    def save(self):
            import markdown
            if self.allow_html == False:
                renderedtext = markdown.markdown(self.body, safe_mode=True)
                self.body_rendered = thumbnailer.shadowbox.run(renderedtext, self.title)
                super(Post, self).save() # Call the "real" save() method.
            else:
                self.body_rendered = markdown.markdown(self.body)
                self.body_rendered = thumbnailer.shadowbox.run(renderedtext, self.title)
                super(Post, self).save() # Call the "real" save() method.

class PostAdmin(admin.ModelAdmin):
    search_fields = ['title','author']
    date_hierarchy = 'created'
admin.site.register(Post, PostAdmin)