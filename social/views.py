from django.shortcuts import render, redirect, get_object_or_404
from .models import Post, Like, Comment
from .forms import PostForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

@login_required
def my_posts_view(request):
  my_posts = Post.objects.filter(author=request.user).order_by('-created_at')

  if request.method == 'POST':
    form = PostForm(request.POST, request.FILES)
    if form.is_valid():
      post = form.save(commit=False)
      post.author = request.user
      post.save()
      return redirect('my_posts')
  else:
    form = PostForm()

  return render(request, 'social/my_posts.html', {'form': form, 'my_posts':my_posts})

@login_required
def post_edit(request, post_id):
    post = get_object_or_404(Post, id=post_id)

    if request.user != post.author:
        return redirect('my_posts')

    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES, instance=post)  # <-- add request.FILES
        if form.is_valid():
            form.save()
            return redirect('my_posts')
    else:
        form = PostForm(instance=post)

    return render(request, 'social/edit_post.html', {'form': form, 'post': post})


@login_required
def post_delete(request, pk):
  post = get_object_or_404(Post, pk=pk)

  if post.author != request.user:
    messages.error(request, "You're not authorized to delete this post")
    return redirect('my_posts')
  
  if request.method == 'POST':
    post.delete()
    messages.success(request, "Post deleted successfully!")
    return redirect('my_posts')
  
  return render(request, 'social/post_confirm_delete.html', {'post':post})

@login_required
def like_post(request, post_id):
  post = get_object_or_404(Post, id=post_id)
  like, created = Like.objects.get_or_create(user=request.user, post=post)
  if not created:
    like.delete() #Unlike
  return redirect('home')

@login_required
def add_comment(request, post_id):
  post = get_object_or_404(Post, id=post_id)
  if request.method == 'POST':
    content = request.POST.get('comment')
    if content:
      Comment.objects.create(user=request.user, post=post, content=content)
  return redirect('home')

def delete_comment(request, comment_id):
   comment = get_object_or_404(Comment, id=comment_id)

   if not comment.can_delete(request.user):
      raise PermissionDenied("You are not authorized to delete this comment")
   
   post_id = comment.post.id
   comment.delete()

   return redirect('home')
