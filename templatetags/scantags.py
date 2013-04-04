from ODKScan_webapp.models import FormImage
from django import template

register = template.Library()

@register.simple_tag
def display_markedup_image(formImageId):
    """Returns HTML for the markedup version of the image with the given id"""
    form_image = FormImage.objects.get(id=formImageId)
    if form_image.status == 'e':
        return ''
    #import sys
    #print >>sys.stderr, dir(form_image.image)
    markedup_image_url = form_image.image.url.partition("photo/")[0] + "markedup.jpg"
    return '<img src="%s"></img>' % markedup_image_url