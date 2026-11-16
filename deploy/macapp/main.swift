// Missions viewer: one window on the Missions page (http://127.0.0.1:8860/). Nothing else.
import Cocoa
import WebKit

let home = URL(string: "http://127.0.0.1:8860/")!
let downPage = """
<html><body style="font:16px -apple-system;background:#111;color:#eee;display:flex;height:100vh;align-items:center;justify-content:center;text-align:center">
<div><p>Missions isn't running.</p><p>Start it: <code>~/missions/deploy/install.sh</code></p>
<p><a href="http://127.0.0.1:8860/" style="color:#6cf">Try again</a></p></div></body></html>
"""

final class App: NSObject, NSApplicationDelegate, WKNavigationDelegate, WKUIDelegate {
    let web = WKWebView(frame: .zero, configuration: WKWebViewConfiguration())
    var window: NSWindow!

    func applicationDidFinishLaunching(_ n: Notification) {
        window = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 1280, height: 860),
                          styleMask: [.titled, .closable, .miniaturizable, .resizable],
                          backing: .buffered, defer: false)
        window.title = "Missions"
        window.contentView = web
        if !window.setFrameUsingName("MissionsMain") { window.center() }
        window.setFrameAutosaveName("MissionsMain")
        web.navigationDelegate = self
        web.uiDelegate = self
        web.load(URLRequest(url: home))
        window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
    }

    func applicationShouldTerminateAfterLastWindowClosed(_ a: NSApplication) -> Bool { true }
    func applicationShouldHandleReopen(_ a: NSApplication, hasVisibleWindows f: Bool) -> Bool {
        window.makeKeyAndOrderFront(nil); return true
    }

    @objc func reload() { web.load(URLRequest(url: home)) }

    // service down: show the plain page (its link goes back to home)
    func fail() { web.loadHTMLString(downPage, baseURL: home) }
    func webView(_ w: WKWebView, didFailProvisionalNavigation n: WKNavigation!, withError e: Error) { fail() }
    func webView(_ w: WKWebView, didFail n: WKNavigation!, withError e: Error) {
        if (e as NSError).code != NSURLErrorCancelled { fail() }
    }

    // other hosts open in the default browser
    func webView(_ w: WKWebView, decidePolicyFor a: WKNavigationAction, decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
        if let u = a.request.url, a.navigationType == .linkActivated, u.host != home.host, u.scheme?.hasPrefix("http") == true {
            NSWorkspace.shared.open(u); decisionHandler(.cancel)
        } else { decisionHandler(.allow) }
    }
    func webView(_ w: WKWebView, createWebViewWith c: WKWebViewConfiguration, for a: WKNavigationAction, windowFeatures f: WKWindowFeatures) -> WKWebView? {
        if let u = a.request.url { NSWorkspace.shared.open(u) }
        return nil
    }

    // alert() / confirm() have no panel in a bare WKWebView: show them as sheets
    func webView(_ w: WKWebView, runJavaScriptAlertPanelWithMessage m: String, initiatedByFrame f: WKFrameInfo, completionHandler: @escaping () -> Void) {
        let a = NSAlert(); a.messageText = m; a.addButton(withTitle: "OK")
        a.beginSheetModal(for: window) { _ in completionHandler() }
    }
    func webView(_ w: WKWebView, runJavaScriptConfirmPanelWithMessage m: String, initiatedByFrame f: WKFrameInfo, completionHandler: @escaping (Bool) -> Void) {
        let a = NSAlert(); a.messageText = m; a.addButton(withTitle: "OK"); a.addButton(withTitle: "Cancel")
        a.beginSheetModal(for: window) { completionHandler($0 == .alertFirstButtonReturn) }
    }

    // mic for the 127.0.0.1 page only
    func webView(_ w: WKWebView, requestMediaCapturePermissionFor o: WKSecurityOrigin, initiatedByFrame f: WKFrameInfo,
                 type: WKMediaCaptureType, decisionHandler: @escaping (WKPermissionDecision) -> Void) {
        decisionHandler(o.host == home.host ? .grant : .deny)
    }
}

func item(_ t: String, _ a: Selector?, _ k: String, _ m: NSEvent.ModifierFlags = .command) -> NSMenuItem {
    let i = NSMenuItem(title: t, action: a, keyEquivalent: k); i.keyEquivalentModifierMask = m; return i
}
func menu(_ title: String, _ items: [NSMenuItem]) -> NSMenuItem {
    let m = NSMenu(title: title); items.forEach { m.addItem($0) }
    let h = NSMenuItem(); h.submenu = m; return h
}

let app = NSApplication.shared
let delegate = App()
app.delegate = delegate
app.setActivationPolicy(.regular)
let bar = NSMenu()
bar.addItem(menu("Missions", [item("Quit Missions", #selector(NSApplication.terminate(_:)), "q")]))
bar.addItem(menu("Edit", [
    item("Undo", Selector(("undo:")), "z"), item("Redo", Selector(("redo:")), "z", [.command, .shift]),
    .separator(), item("Cut", #selector(NSText.cut(_:)), "x"), item("Copy", #selector(NSText.copy(_:)), "c"),
    item("Paste", #selector(NSText.paste(_:)), "v"), item("Select All", #selector(NSText.selectAll(_:)), "a")]))
let reload = item("Reload", #selector(App.reload), "r"); reload.target = delegate
bar.addItem(menu("View", [reload]))
bar.addItem(menu("Window", [item("Close", #selector(NSWindow.performClose(_:)), "w")]))
app.mainMenu = bar
app.run()
