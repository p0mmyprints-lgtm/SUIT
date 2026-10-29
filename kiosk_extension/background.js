// SUIT Kiosk Extension - Background Service Worker
// Communicates with native host com.suit.kiosk via Chrome Native Messaging API
// and manages tab operations (opening board config, closing tab to return)

// ---------------------------------------------------------------------------
// Kiosk tab housekeeping
// Autodarts 2.1 opens the Board Manager in a NEW tab at the board's LAN address
// (e.g. http://192.168.0.192:3180), and the Board Manager's own "Play" link opens
// yet another tab. The kiosk has no tab bar, so these pile up with no way back.
// Rules, applied only to newly opened tabs:
//   - board LAN address :3180 -> reopen as localhost:3180 (gets the Back button)
//   - new Play tab           -> becomes the only tab
//   - new Board Manager tab  -> replaces any older Board Manager tab
//   - any other website      -> closed (keeps the kiosk on Autodarts)
// ---------------------------------------------------------------------------
const BOARD_PORT = "3180";
const newTabs = new Set();

function isLocalHost(host) {
  return host === "localhost" || host === "127.0.0.1";
}

function isLanHost(host) {
  return /^(10\.|192\.168\.|172\.(1[6-9]|2\d|3[01])\.|169\.254\.)/.test(host) || host.endsWith(".local");
}

function isAutodartsHost(host) {
  return host === "autodarts.com" || host.endsWith(".autodarts.com") ||
         host === "autodarts.io" || host.endsWith(".autodarts.io") || host.endsWith(".autodarts.direct");
}

function parseUrl(url) {
  try {
    return new URL(url);
  } catch (e) {
    return null;
  }
}

function isBoardManager(u) {
  return u && isLocalHost(u.hostname) && u.port === BOARD_PORT;
}

function isPlay(u) {
  return u && u.hostname === "play.autodarts.com";
}

async function closeTabs(tabs) {
  for (const t of tabs) {
    try {
      await chrome.tabs.remove(t.id);
    } catch (e) {
      // already gone
    }
  }
}

async function tidyNewTab(tabId, url) {
  const u = parseUrl(url);
  if (!u || !/^https?:$/.test(u.protocol)) return; // about:blank etc. - wait for the real URL
  newTabs.delete(tabId);

  if (u.port === BOARD_PORT && isLanHost(u.hostname)) {
    const local = `http://localhost:${BOARD_PORT}${u.pathname}${u.search}${u.hash}`;
    newTabs.add(tabId); // re-check once it lands on localhost
    chrome.tabs.update(tabId, { url: local });
    return;
  }

  const others = (await chrome.tabs.query({})).filter((t) => t.id !== tabId);
  if (others.length === 0) return;

  if (isPlay(u)) {
    await closeTabs(others);
  } else if (isBoardManager(u)) {
    await closeTabs(others.filter((t) => isBoardManager(parseUrl(t.pendingUrl || t.url))));
  } else if (!isAutodartsHost(u.hostname) && !isLocalHost(u.hostname)) {
    await closeTabs([{ id: tabId }]);
  }
}

chrome.tabs.onCreated.addListener((tab) => {
  newTabs.add(tab.id);
  const url = tab.pendingUrl || tab.url;
  if (url) tidyNewTab(tab.id, url);
});

chrome.tabs.onUpdated.addListener((tabId, changeInfo) => {
  if (changeInfo.url && newTabs.has(tabId)) tidyNewTab(tabId, changeInfo.url);
});

chrome.tabs.onRemoved.addListener((tabId) => newTabs.delete(tabId));

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (!request || !request.action) {
    sendResponse({ status: "error", error: "No action specified" });
    return false;
  }

  // 1. Handle Tab Operations
  if (request.action === "close_tab") {
    if (sender && sender.tab && sender.tab.id) {
      // Closing the last tab would quit the kiosk - go back to Autodarts in place instead
      chrome.tabs.query({}, (tabs) => {
        if (tabs.length <= 1) {
          chrome.tabs.update(sender.tab.id, { url: "https://play.autodarts.com/" }, () => sendResponse({ status: "ok" }));
        } else {
          chrome.tabs.remove(sender.tab.id, () => sendResponse({ status: "ok" }));
        }
      });
    } else {
      chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
        if (tabs && tabs[0] && tabs[0].id) {
          chrome.tabs.remove(tabs[0].id, () => sendResponse({ status: "ok" }));
        } else {
          sendResponse({ status: "error", error: "No active tab found" });
        }
      });
    }
    return true;
  }

  if (request.action === "open_tab") {
    const targetUrl = request.url || "http://localhost:3180/config";
    chrome.tabs.create({ url: targetUrl }, (tab) => {
      sendResponse({ status: "ok", tabId: tab ? tab.id : null });
    });
    return true;
  }

  // 2. Handle System Operations via Native Messaging
  try {
    chrome.runtime.sendNativeMessage(
      "com.suit.kiosk",
      request,
      (response) => {
        if (chrome.runtime.lastError) {
          console.error("SUIT Kiosk Native Message error:", chrome.runtime.lastError.message);
          sendResponse({
            status: "error",
            error: chrome.runtime.lastError.message
          });
        } else {
          sendResponse(response || { status: "ok" });
        }
      }
    );
  } catch (err) {
    console.error("Failed sending native message:", err);
    sendResponse({ status: "error", error: String(err) });
  }

  return true; // Required to keep sendResponse valid asynchronously
});
