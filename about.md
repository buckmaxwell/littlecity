

How to use this site
====================

There are some pretty neat things you can do with an anonymous shared wall social network.
I'll leave you to figure them out own your own, but here is a few hints.

 + Art - do some cool ascii art
 + PGP keys/RSA encoded messages - share your public key with a friend and communicate
   with them while everyone watches in confusion
 + Socal commentary - give your perspecives and see how the world reacts
 + Defacement - Unleash your rage at the world by destroying what others have created
 + Link Sharing - Toss up links to your sound cloud, news, funny videos, articles, and more
 + Selling items - everybody likes items
 + CSS/HTML and JavaScript Practice - b3c0m3 h4ck3r
 + Law and Order - Perhaps you feel there should be a supreme ruler of this website and 
   it should be you.  Try to enforce it.  Add password protection to the edit buttons and
   javascript to the page that makes calls to an api that removes content you don't like before
   publishing.
 + Law and Order 2 - Hold a democratic election on this site proposing issues and making
   decisions about how to use this site.
 + Demands - Have advice about how this website should be run?  Just make a post on the page.
 + Outsourcing - want this website to look a certain way?  Hire a team abroad to make sure it
   does
 + Free Advertising - Put an add up and then hammer the site with edit requests so that no one 
   else can edit.  Your add will stay up for the cost of keeping a computer running.
   Hint:  Everyone will stop using the site (and not see your add) because  the content will go 
   stale if you do this.  Maybe put up an add people like, and it will stay there (for a while)
 + Games - create cool interactive games to play with fellow site users
 + Anything else you can think of - literally, anything else you can think of


FAQ
===

Q Can I traverse in time?
A No, but I can, and you will be able to soon.  Gimme a week or so.

Q Won't people destroy the site just because they can?
A Probably, but that's ok.

Q Am I really anonymous on here?
A No, not completely.  You can be, but you'd have to do some things first.  Your IP address is 
  public, and unless you are behind a proxy or TOR everything could be traced back to you.

Q Is this site add supported, profitable, have a financial point?
A No.

Q Can I view the code for this site on GitHub? Can I submit PRs if your code is shitty?
A Sure to both! https://github.com/buckmaxwell/littlecity.  


Fixing common site issues
=========================

1. The edit text/css buttons are gone!!

    To edit the text visit http://littlecity.herokuapp.com/text/edit
    css is at http://littlecity.herokuapp.com/css/edit

2. The page is invisible
    
    Someone has likely added "display:none" somewhere in the css page or 
    the inline css page, or someone had added javascript at the bottom
    of the page to delete text dynamically.  Remove it to make the page
    visible again.

    It's also possible someone has linked to an external stylesheet that
    has dispay set to none.  If they did that, remove the link to the bad 
    stylesheet.

3. The style changes in style.css do not show up
    
    It's possible that someone has added a link to a different style
    sheet in the text section that has disagreeing css.  If you can find
    it and you don't like that, delete the reference to it.

4. The page redirects somewhere else

    Something is wacky in the text file.  To find it and delete it do 
    http://littlecity.herokuapp.com/text/edit


API Documentation
=================

 GET / 
 
  Fetch a redirect to the most recent history item

 GET /history/:id
  
  Fetch the history item with the id given.  If the item does not exist, you will get a redirect to 
  a oldest item that does exist, and is greater than the id supplied

 POST /text

  Post the full content of what the new page should look like

 POST /css
  
  Post the full content of what the css should look like

 GET /unique_vistors

  Fetch the number of unique visitors that have used the site since we started counting (9/5/2016)
  in JSON format

 GET /info

  Fetch info about this site and how to use it
 

Thanks
======

Thanks for using this goofy site! Have a lot of fun.

- squiggleboy63

