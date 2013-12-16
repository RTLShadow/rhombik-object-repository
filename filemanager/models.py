from django.db import models
from thumbnailer import thumbnailer2
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.conf import settings
import zipfile
from io import BytesIO
import os.path
from django.core.files.uploadedfile import InMemoryUploadedFile


class fakefile():
    def url():
        return("null")

# Create your models here.

class fileobject(models.Model):

    def uploadpath(instance, filename):
        return ("uploads/"+str(instance.project.id)+instance.subfolder+filename)


    project = models.ForeignKey('project.Project')
    subfolder = models.CharField(max_length=256, default="/")
    filename = models.FileField(upload_to=uploadpath)
    filetype = models.CharField(max_length=16, blank=True, null=True, default="norender")


    def __unicode__(self):
        return str(self.filename)


    def save(self):
        super(fileobject, self).save()

        self.filetype = thumbnailer2.thumbnailify(self, (0,0))[1]
        super(fileobject, self).save()

    def delete(self, *args, **kwargs):
        super(fileobject, self).delete(*args, **kwargs)
        default_storage.delete(self.filename)
       #default_storage.delete(self.thumbname)


class thumbobject(models.Model):
    #A pointer to the file this is a thumbnail of.
    fileobject = models.ForeignKey(fileobject)
    #This is the actual thumbnail, stored using django storage, whatever that may be.
    filename = models.FileField(upload_to="thumbs/", blank=True, null=True)
    #What the file type is
    filetype = models.CharField(max_length=16, blank=True, null=True)
    #the size of the file.
    filex = models.PositiveSmallIntegerField()
    filey = models.PositiveSmallIntegerField()
    
    class Meta:
        unique_together = ('filex', 'filey', "fileobject")

    def save(self, generate=True, *args, **kwargs):
        from filemanager.tasks import thumbTask
        if generate==True:
            if self.pk:
                self.delete()
            thumbTask.delay(self)
            self.filetype="norender"
            self.filename=fakefile()
            return
        else:
            super(thumbobject, self,).save()

    def delete(self, *args, **kwargs):
        super(thumbobject, self).delete(*args, **kwargs)
        default_storage.delete(self.filename)

class thumbObjectProxy(thumbobject):

    class Meta:
        proxy = True
    def save(self, *args, **kwargs):
        self=self
        tmpfile, self.filetype = thumbnailer2.thumbnailify(self.fileobject, (self.filex, self.filey))
        #Bleh, this is awful. Means we won't have to refactor a bunch of other stuff, but implies some deeper architecture issues.
        if self.filetype=="text":
            self.filetype="norender"
        self.filename = tmpfile
        super(thumbObjectProxy, self,).save(generate=False, *args, **kwargs)


from django.core.files.uploadedfile import UploadedFile
from io import BytesIO

class zippedobject(models.Model):

    project = models.ForeignKey('project.Project', unique=True)
    filename = models.FileField(upload_to="projects/", blank=True, null=True)
    def save(self, generate=True, *args, **kwargs):
        from filemanager.tasks import zippedTask
        if generate==True:
            if self.pk:
                self.delete()
            zippedTask.delay(self.project)
            self.filename=fakefile()
            return
        else:
            super(zippedobject, self,).save()

class zippedObjectProxy(zippedobject):

    class Meta:
        proxy = True
    def save(self, *args, **kwargs):
        s = BytesIO()

        data = zipfile.ZipFile(s,'a')
        projectfiles = fileobject.objects.filter(project=self.project)
        for filedata in projectfiles:
            filed = filedata.filename.read()
            pathAndName = str(self.project.title)+filedata.subfolder+os.path.split(str(filedata.filename))[1] #### this is where subfolders will be added to inside the zip file.
            data.writestr(pathAndName, filed)
        data.close()
        s.seek(0)
        filedata = UploadedFile(s)
        filedata.name = self.project.title+".zip"
        self.filename = filedata
        super(zippedObjectProxy, self,).save(generate=False, *args, **kwargs)

import thumbnailer.shadowbox
import markdown

class htmlobject(models.Model):
    #A pointer to the file this is a thumbnail of.
    fileobject = models.ForeignKey(fileobject, unique=True)
    body_rendered = models.TextField('Entry body as HTML', blank=True, null=True)

    def save(self, *args, **kwargs):
        self.body_rendered = markdown.markdown(self.fileobject.filename.read(), safe_mode=True)
        super(htmlobject, self).save(*args, **kwargs)

