---
title: <% tp.file.title %><% tp.file.cursor(1) %>
aliases: [<% tp.user.extractNamesFromString(tp.file.title) %><% tp.file.cursor(1) %>]
tags: []
id: <% tp.file.creation_date("YYYYMMDDHHmmss") %>
published: <% tp.file.creation_date("YYYY-MM-DD") %>
image: "../../assets/images/svg/undraw/undraw_scrum_board.svg"
description:
category: diary
---

<%*

await tp.file.rename(tp.file.creation_date("YYYYMMDDHHmmss"))

%>

# <% tp.file.title %><% tp.file.cursor(1) %>
