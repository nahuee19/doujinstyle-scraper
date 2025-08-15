# doujinstyle-scraper
Ethically scrapes doujinstyle.com.

> [!IMPORTANT]
> **Work in progress** *(nothing so far! -a literal stub right now)*

## doujinstyle.com 🌐

> DoujinStyle functions as an index of content found publicly on the Internet

*[https://doujinstyle.com/?p=dmca](https://doujinstyle.com/?p=dmca)*

In this case, "content" being mostly music.

## Format 📦

Exports each entry into a singular JSON file containing W.I.P.

## Time & Breakage ⏳

Since we are scraping and parsing from the website's public HTTP, and not from any kind of API, it is very likely this project will not
last long into time. The website need only become prettier, modifying or adding HTML, the existing parser will most likely break.

It is also likely the website may modernize in a way that adds a cruel CAPTCHA or rate limiter.

There is also the possibility of the website being taken down, somehow. At the time of writing this, it is written "Version 3" near the
site's logo, implying other versions of the website might have been taken down, or just modernized.

![dslogo](data:image/png;base64,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)

<img src="data:image/png;base64,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" alt="Example" />


## Motivation 💿

While searching for a high quality FLAC recording of [LEMON MELON COOKIE](https://youtu.be/5l8VZEyNRH8) ([TAK](https://www.youtube.com/channel/UCktjMRvuBnE_XLVWIMa2H1w)), I stumbled upon this website, it immediately sparked a flame of need within me; the need to **SCRAPE**; doujinstyle.com
looked so *docile and scrapable*, I couldn't resist but to scrape it to the bone!

## Requests & Inner Workings ⚡

Let N be the number of IDs you want to fetch.
The program does 2 * N HTTP requests:

* One HTTP GET to fetch the contents of the page item.
* One HTTP POST on the download form to fetch the download link.

POST also redirects, it may be more than 2 * N, but for the sake of simplicity we'll say it's 2 * N.

I reckon this POST request allows the website to count the number of times an item has been downloaded,
visible with the `# of Downloads:` label on each item.

---

> [!NOTE]
> Replace `<item_id>` with the ID of the item.

1. The HTTP GET URL request is like so:
```text
https://doujinstyle.com/?p=page&type=1&id=<item_id>
```

This returns the normal HTTP that is also sent when visiting via a web browser.


2. The HTTP POST request data is as follows:
```json
{
  "type": "1",
  "id": "<item_id>",
  "source": "0",
  "download_link": ""
}
```

This returns the download link linked with the item (usually Mediafire or Mega).

It can be sent to either an item URL `https://doujinstyle.com/?p=page&type=1&id=<item_id>` or directly
the base URL `https://doujinstyle.com/`, both seem to work.

Concerning the values of the POST data:

* `type`: I don't know what it means, only that sometimes, e.g., ID=6, when setting it to `1`
this download URL is returned:
```text
https://mega.nz/#!ZE5UXYIA!VYp8h5mG1_pgQA8PebVN0gEElMjNAOijtUZf-_-dxLc
```  
And when setting it to `2`, this one is returned:
```text
https://mega.nz/#!8QMF3YBI!Bj7OJnXHpfTBnr6jfY5O_k_oXVyEV8OMUpPIxH1OERM
```  
Different URLs, the first one seems is the good one though, that when a user clicks on the 'Download' button,
it redirects to the same URL.

* `id`: The item ID.

* `source`: I don't know what it means. It is set by default to `0`. Maybe a different CDN, however when
set to `1` the posted URL is returned, not the download link. When set to `` (empty string), the POST
request still seems to function.

* `download_link`: I don't know what it means. Only that it is required to exist with an empty string for
the download URL to be returned, otherwise, the posted URL is returned.


## Find Highest Item ID

1. Visit [doujinstyle.com](https://doujinstyle.com/) and click on the title of the latest item (top left hand corner)
2. Copy the URL's ID following this format: `https://doujinstyle.com/?p=page&type=1&id=<item_id>`
3. `<item_id>` is the latest, highest ID.

