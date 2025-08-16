# doujinstyle-scraper

Ethically scrapes doujinstyle.com.

> [!IMPORTANT]
> **Work in progress** *(nothing so far! -a literal stub right now)*

## doujinstyle.com 🌐

> DoujinStyle functions as an index of content found publicly on the Internet

*[https://doujinstyle.com/?p=dmca](https://doujinstyle.com/?p=dmca)*

In this case, "content" being mostly music.

> [!WARNING]
> Tested and developed using Python 3.13. I don't expect the app to run beneath 3.12.

## Format 📦

Exports each entry into a singular JSON file containing W.I.P.

## Time & Breakage ⏳

Since we are scraping and parsing from the website's public HTTP, and not from any kind of API, it is very likely this
project will not
last long into time. The website need only become prettier, modifying or adding HTML, the existing parser will most
likely break.

It is also likely the website may modernize in a way that adds a cruel CAPTCHA or rate limiter.

There is also the possibility of the website being taken down, somehow. At the time of writing this, it is written "
Version 3" near the
site's logo, implying other versions of the website might have been taken down, or just modernized.

![doujinstyle site logo](./doujinstyle-logo.png)

## Motivation 💿

While searching for a high quality FLAC recording
of [LEMON MELON COOKIE](https://youtu.be/5l8VZEyNRH8) ([TAK](https://www.youtube.com/channel/UCktjMRvuBnE_XLVWIMa2H1w)),
I stumbled upon this website, it immediately sparked a flame of need within me; the need to **SCRAPE**; doujinstyle.com
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

### App Components

The app has three main components:

* The `logger` which initializes an app logger.
* The `fetcher` which does all the asynchronous requests to the website.
* The `parser` which parses the response from the `fetcher` to get usable data.

The `fetcher` and `parser` communicate via a callback function that is called whenever the `fetcher` fetched
the data.

## Find Highest Item ID 🗻

1. Visit [doujinstyle.com](https://doujinstyle.com/) and click on the title of the latest item (top left hand corner)
2. Copy the URL's ID following this format: `https://doujinstyle.com/?p=page&type=1&id=<item_id>`
3. `<item_id>` is the latest, highest ID.

