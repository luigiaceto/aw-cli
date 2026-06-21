import Cocoa
import Darwin
import WebKit

final class AppDelegate: NSObject, NSApplicationDelegate, WKNavigationDelegate {
    private var window: NSWindow?
    private var webView: WKWebView?
    private var backendProcess: Process?
    private var backendURL: URL?

    func applicationDidFinishLaunching(_ notification: Notification) {
        NSApp.setActivationPolicy(.regular)
        buildMenu()

        let port = findAvailablePort() ?? 8765
        backendURL = URL(string: "http://127.0.0.1:\(port)/")

        createWindow()
        startBackend(port: port)
        waitForBackend(attemptsRemaining: 80)
        NSApp.activate(ignoringOtherApps: true)
    }

    func applicationWillTerminate(_ notification: Notification) {
        stopBackend()
    }

    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool {
        true
    }

    private func buildMenu() {
        let mainMenu = NSMenu()
        let appMenuItem = NSMenuItem()
        let appMenu = NSMenu()
        appMenu.addItem(
            NSMenuItem(
                title: "Chiudi AwWeb",
                action: #selector(NSApplication.terminate(_:)),
                keyEquivalent: "q"
            )
        )
        appMenuItem.submenu = appMenu
        mainMenu.addItem(appMenuItem)
        NSApp.mainMenu = mainMenu
    }

    private func createWindow() {
        let configuration = WKWebViewConfiguration()
        configuration.allowsAirPlayForMediaPlayback = true
        configuration.mediaTypesRequiringUserActionForPlayback = []

        let webView = WKWebView(frame: .zero, configuration: configuration)
        webView.navigationDelegate = self
        webView.allowsBackForwardNavigationGestures = true
        self.webView = webView

        let window = NSWindow(
            contentRect: NSRect(x: 0, y: 0, width: 1280, height: 820),
            styleMask: [.titled, .closable, .miniaturizable, .resizable],
            backing: .buffered,
            defer: false
        )
        window.title = "AwWeb"
        window.center()
        window.contentView = webView
        window.makeKeyAndOrderFront(nil)
        self.window = window
    }

    private func startBackend(port: UInt16) {
        guard let resourceURL = Bundle.main.resourceURL else {
            showFatalError("Risorse dell'app non trovate.")
            return
        }

        let executableURL = resourceURL
            .appendingPathComponent("backend")
            .appendingPathComponent("aw-web-backend")

        guard FileManager.default.isExecutableFile(atPath: executableURL.path) else {
            showFatalError("Backend aw-web non trovato dentro l'app.")
            return
        }

        let process = Process()
        process.executableURL = executableURL
        process.currentDirectoryURL = executableURL.deletingLastPathComponent()
        process.environment = ProcessInfo.processInfo.environment.merging(
            [
                "AW_WEB_HOST": "127.0.0.1",
                "AW_WEB_PORT": String(port),
                "AW_WEB_NO_BROWSER": "1",
                "PYTHONUNBUFFERED": "1",
            ],
            uniquingKeysWith: { _, new in new }
        )

        let output = Pipe()
        process.standardOutput = output
        process.standardError = output

        do {
            try process.run()
            backendProcess = process
        } catch {
            showFatalError("Impossibile avviare il backend: \(error.localizedDescription)")
        }
    }

    private func stopBackend() {
        guard let process = backendProcess, process.isRunning else {
            return
        }
        process.terminate()
        DispatchQueue.global(qos: .utility).asyncAfter(deadline: .now() + 1.0) {
            if process.isRunning {
                process.interrupt()
            }
        }
    }

    private func waitForBackend(attemptsRemaining: Int) {
        guard attemptsRemaining > 0, let url = backendURL else {
            showFatalError("Il backend non ha risposto in tempo.")
            return
        }

        var request = URLRequest(url: url)
        request.timeoutInterval = 0.5
        URLSession.shared.dataTask(with: request) { [weak self] _, response, _ in
            DispatchQueue.main.async {
                if let httpResponse = response as? HTTPURLResponse, httpResponse.statusCode < 500 {
                    self?.webView?.load(URLRequest(url: url))
                } else {
                    DispatchQueue.main.asyncAfter(deadline: .now() + 0.1) {
                        self?.waitForBackend(attemptsRemaining: attemptsRemaining - 1)
                    }
                }
            }
        }.resume()
    }

    func webView(
        _ webView: WKWebView,
        decidePolicyFor navigationAction: WKNavigationAction,
        decisionHandler: @escaping (WKNavigationActionPolicy) -> Void
    ) {
        guard
            navigationAction.navigationType == .linkActivated,
            let url = navigationAction.request.url,
            url.host != "127.0.0.1"
        else {
            decisionHandler(.allow)
            return
        }

        NSWorkspace.shared.open(url)
        decisionHandler(.cancel)
    }

    private func showFatalError(_ message: String) {
        let alert = NSAlert()
        alert.messageText = "AwWeb non puo avviarsi"
        alert.informativeText = message
        alert.alertStyle = .critical
        alert.runModal()
        NSApp.terminate(nil)
    }
}

let app = NSApplication.shared
let delegate = AppDelegate()
app.delegate = delegate
app.run()

private func findAvailablePort() -> UInt16? {
    let socketFD = socket(AF_INET, SOCK_STREAM, 0)
    guard socketFD >= 0 else {
        return nil
    }
    defer {
        close(socketFD)
    }

    var value: Int32 = 1
    setsockopt(socketFD, SOL_SOCKET, SO_REUSEADDR, &value, socklen_t(MemoryLayout<Int32>.size))

    var address = sockaddr_in()
    address.sin_len = UInt8(MemoryLayout<sockaddr_in>.size)
    address.sin_family = sa_family_t(AF_INET)
    address.sin_port = 0
    address.sin_addr = in_addr(s_addr: inet_addr("127.0.0.1"))

    let bindResult = withUnsafePointer(to: &address) { pointer in
        pointer.withMemoryRebound(to: sockaddr.self, capacity: 1) { socketAddress in
            bind(socketFD, socketAddress, socklen_t(MemoryLayout<sockaddr_in>.size))
        }
    }
    guard bindResult == 0 else {
        return nil
    }

    var length = socklen_t(MemoryLayout<sockaddr_in>.size)
    let nameResult = withUnsafeMutablePointer(to: &address) { pointer in
        pointer.withMemoryRebound(to: sockaddr.self, capacity: 1) { socketAddress in
            getsockname(socketFD, socketAddress, &length)
        }
    }
    guard nameResult == 0 else {
        return nil
    }

    return UInt16(bigEndian: address.sin_port)
}
