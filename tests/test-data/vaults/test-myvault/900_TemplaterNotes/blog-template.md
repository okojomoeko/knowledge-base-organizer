---
<%* const title = await tp.system.prompt('記事タイトルを入力') %>
title: <%* tR += title %>
aliases: [<%* tR += title %>]
tags: []
id: <% tp.file.creation_date("YYYYMMDDHHmmss") %>
published: <% tp.file.creation_date("YYYY-MM-DD") %>
image: "../../assets/images/svg/undraw/undraw_scrum_board.svg"
description:
category: diary
---

import ImgModal from '../../components/ImgModal.astro'

<%*

await tp.file.rename(tp.file.creation_date(`${title}`))

%>
