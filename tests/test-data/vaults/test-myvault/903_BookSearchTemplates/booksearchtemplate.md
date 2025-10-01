---
title: "{{title}}"
tags: [📚Book]
state: unread
isStock: false
subtitle: "{{subtitle}}"
author: [{{author}}]
authors: [{{authors}}]
category: [{{category}}]
categories: [{{categories}}]
publisher: {{publisher}}
publishDate: {{publishDate}}
totalPage: {{totalPage}}
coverUrl: {{coverUrl}}
coverSmallUrl: {{coverSmallUrl}}
description: "{{description}}"
link: {{link}}
previewLink: {{previewLink}}
isbn13: {{isbn13}}
isbn10: {{isbn10}}
---

<%* if (tp.frontmatter.cover && tp.frontmatter.cover.trim() !== "") { tR += `![cover|150](${tp.frontmatter.cover})` } %>

<%* if (tp.frontmatter.localCover && tp.frontmatter.localCover.trim() !== "") { tR += `![[${tp.frontmatter.localCover}|150]]` } %>

# {{title}}
