from django.template import loader, RequestContext
from django.core.exceptions import ImproperlyConfigured
from django.http import (HttpResponse, HttpResponseRedirect, Http404, 
                         HttpResponseForbidden)
from secretballot.models import Vote

def vote(request, content_type, object_id, vote, can_vote_test=None,
              redirect_url=None, template_name=None, template_loader=loader,
              extra_context=None, context_processors=None, mimetype=None):

    # get the token from a SecretBallotMiddleware 
    if not hasattr(request, 'secretballot_token'):
        raise ImproperlyConfigured('To use secretballot a SecretBallotMiddleware must be installed. (see secretballot/middleware.py)')
    token = request.secretballot_token

    # do the action
    if vote:

        # if there is a can_vote_test func specified, test then 403 if needed
        if can_vote_test and not can_vote_test(request, content_type, 
                                                object_id, vote):
            return HttpResponseForbidden("vote was forbidden")

        # 404 if object to be voted upon doesn't exist
        if content_type.model_class().objects.filter(pk=object_id).count() == 0:
            raise Http404


        vobj,new = Vote.objects.get_or_create(content_type=content_type,
                                              object_id=object_id, token=token,
                                              defaults={'vote':vote})
        if not new:
            vobj.vote = vote
            vobj.save()
    else:
        Vote.objects.filter(content_type=content_type, 
                            object_id=object_id, token=token).delete() 

    # build the response
    if redirect_url:
        return HttpResponseRedirect(redirect_url)
    elif template_name:
        content_obj = content_type.get_object_for_this_type(pk=object_id)
        c = RequestContext(request, {'content_obj':content_obj}, 
                           context_processors)

        # copy extra_context into context, calling any callables
        for k,v in extra_context.items():
            if callable(v):
                c[k] = v()
            else:
                c[k] = v

        t = template_loader.get_template(template_name)
        body = t.render(c)
    else:
        votes = Vote.objects.filter(content_type=content_type,
                                    object_id=object_id).count()
        body = "{'num_votes':%d}" % votes

    return HttpResponse(body, mimetype=mimetype)
