// Dharalu for Mac - a menu-bar companion to the Dharalu dashboard (ధరలు, "prices").
//
// It reads the summary.json the agent publishes (wheat, gold, silver, platinum), checks the
// world gold / silver / platinum price live every few minutes, shows the call you pick in the
// menu bar with the proof behind it, notifies you when a call changes or a price jumps, and
// opens the full dashboard in its own window.
// Nothing is predicted here - the agent does that; this app only reads its output.

import AppKit
import ServiceManagement
import UserNotifications
import WebKit

let appName = "Dharalu"
let defaultDataURL = "https://sravankumartangudu.github.io/dharalu/data/summary.json"
let repoURL = "https://github.com/Sravankumartangudu/dharalu"
let liveURL = "https://api.gold-api.com/price/"
let defaultOrder = ["wheat", "gold", "silver", "platinum"]

// MARK: - Settings

enum Settings {
    static let d = UserDefaults.standard
    static var dataURL: String {
        get { d.string(forKey: "dataURL") ?? defaultDataURL }
        set { d.set(newValue, forKey: "dataURL") }
    }
    static var siteURL: URL {
        let s = dataURL.replacingOccurrences(of: "data/summary.json", with: "")
        return URL(string: s) ?? URL(string: "https://sravankumartangudu.github.io/dharalu/")!
    }
    static func pageURL(_ hash: String) -> URL {
        URL(string: siteURL.absoluteString + "#" + hash) ?? siteURL
    }
    /// Which commodity the menu bar shows.
    static var barItem: String {
        get { let v = d.string(forKey: "barItem") ?? "wheat"; return defaultOrder.contains(v) ? v : "wheat" }
        set { d.set(newValue, forKey: "barItem") }
    }
    static var showPrice: Bool {
        get { d.object(forKey: "showPrice") as? Bool ?? true }
        set { d.set(newValue, forKey: "showPrice") }
    }
    static var notify: Bool {
        get { d.object(forKey: "notify") as? Bool ?? true }
        set { d.set(newValue, forKey: "notify") }
    }
    static let minuteOptions = [5, 15, 30, 60]
    static var minutes: Int {
        get { let v = d.object(forKey: "minutes") as? Int ?? 5; return minuteOptions.contains(v) ? v : 5 }
        set { d.set(newValue, forKey: "minutes") }
    }
    /// "system" (follow macOS, Auto included), "light" or "dark".
    static var appearance: String {
        get { let v = d.string(forKey: "appearance") ?? "system"; return ["system", "light", "dark"].contains(v) ? v : "system" }
        set { d.set(newValue, forKey: "appearance") }
    }
    static func applyAppearance() {
        switch appearance {
        case "light": NSApp.appearance = NSAppearance(named: .aqua)
        case "dark": NSApp.appearance = NSAppearance(named: .darkAqua)
        default: NSApp.appearance = nil
        }
    }
    /// JS that makes the dashboard page match the choice (same `dh.theme` key the page's own toggle uses).
    static var themeScript: String {
        let v = appearance
        return v == "system"
            ? "try{localStorage.removeItem('dh.theme');delete document.documentElement.dataset.theme;}catch(e){}"
            : "try{localStorage.setItem('dh.theme','\"\(v)\"');document.documentElement.dataset.theme='\(v)';}catch(e){}"
    }
    /// 📍 Which place the wheat landed cost, margins and 📍 lines are for ("srikakulam", "hyderabad").
    /// The dashboard page keeps the same choice in `dh.place`.
    static var place: String {
        get { d.string(forKey: "place") ?? "srikakulam" }
        set { d.set(newValue, forKey: "place") }
    }
    static var placeScript: String {
        let k = place.filter { $0.isLetter || $0.isNumber || $0 == "-" }
        return "try{localStorage.setItem('dh.place','\"\(k)\"');}catch(e){}"
    }
    static func lastSignal(_ k: String) -> String? { d.string(forKey: "lastSignal.\(k)") }
    static func setLastSignal(_ k: String, _ v: String?) { d.set(v, forKey: "lastSignal.\(k)") }
    static func lastMove(_ k: String) -> String? { d.string(forKey: "lastMove.\(k)") }
    static func setLastMove(_ k: String, _ v: String) { d.set(v, forKey: "lastMove.\(k)") }
}

// MARK: - The agent's output (docs/data/summary.json)

struct Summary: Decodable {
    /// Since 2.2 each rule's points are multiplied by a weight learned from its own record,
    /// so the counted points and the score can be fractional.
    struct Evidence: Decodable {
        let rule: String; let value: String; let test: String; let points: Double; let source: String; let why: String?
        let weight: Double?; let counted: Double?
    }
    struct Equal: Decodable { let score: Double; let key: String; let label: String }
    struct Signal: Decodable {
        let score: Double; let max_score: Double; let confidence: String; let key: String
        let label: String; let telugu: String; let buyer: String; let holder: String
        let plain: String?; let record_line: String?; let change_line: String?; let confidence_why: [String]?
        let trend_cap: String?; let pending: String?; let equal: Equal?
    }
    struct Changes: Decodable { let since: String; let label_was: String?; let call_changed: Bool? }
    struct LongTerm: Decodable { let key: String; let label: String; let telugu: String?; let advice: String; let why: String?; let record_line: String? }
    struct Point: Decodable { let date: String; let price: Double; let low: Double; let high: Double }
    struct Group: Decodable { let scope: String?; let days: Int; let avg_move_pct: Double; let rose_pct: Double; let beat_holding_cost_pct: Double? }
    struct Record: Decodable { let same_call: Group?; let live_right_pct: Double?; let live_graded: Int? }
    struct Briefing: Decodable { let source: String?; let english: String; let telugu: String }
    struct Timing: Decodable { let cheapest_months: [String]; let dearest_months: [String]; let days_to_buy_window: Int? }
    /// Metals only: the agent's world price and the factor that turns US$/oz into ₹ for the unit shown.
    struct Live: Decodable { let symbol: String; let usd: Double; let factor: Double; let prev_close: Double?; let updated: String? }
    struct ForecastWhy: Decodable { let summary: String?; let biggest: String? }
    /// Which place the price is from (wheat: the benchmark mandis; metals: the all-India import price).
    struct Where: Decodable { let short: String; let detail: String?; let landed: String?; let place_note: String? }
    /// The places a trader can pick (since 2.4): Srikakulam, Hyderabad.
    struct Place: Decodable { let key: String; let name: String; let state: String; let telugu: String?; let `default`: Bool? }
    struct Item: Decodable {
        let key: String
        let asof: String
        let generated_at: String?
        let signal: Signal
        let evidence: [Evidence]
        let forecast30: Point?
        /// Why the forecast says what it says (summary + its biggest part).
        let forecast_why: ForecastWhy?
        let record: Record?
        let changes: Changes?
        let long_term: LongTerm?
        let briefing: Briefing
        let timing: Timing?
        let carrying_cost_30d_pct: Double?
        let label: String
        let telugu_name: String?
        let emoji: String
        let unit: String
        let unit_short: String
        let price: Double
        let chg_1d: Double?
        let chg_7d: Double?
        let chg_30d: Double?
        let move_alert_pct: Double?
        let live: Live?
        let lines: [String]?
        let `where`: Where?
        /// Since 2.4: the same, for each place (wheat landed cost differs; metals are one all-India price).
        let lines_by_place: [String: [String]]?
        let where_by_place: [String: Where]?
    }

    let generated_at: String
    let order: [String]?
    let items: [String: Item]
    let places: [Place]?

    /// The chosen place if this data knows it, else the default place.
    var place: Place? {
        let ps = places ?? []
        return ps.first { $0.key == Settings.place } ?? ps.first { $0.default == true } ?? ps.first
    }

    var generated: Date? { isoDate(generated_at) }
    var keys: [String] { (order ?? defaultOrder).filter { items[$0] != nil } }
}

/// A live price from gold-api.com, already turned into ₹ for the commodity's unit.
struct LivePrice { let rs: Double; let at: Date }

// MARK: - Formatting

func isoDate(_ s: String) -> Date? {
    let f = ISO8601DateFormatter()
    if let d = f.date(from: s) { return d }
    f.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
    return f.date(from: s)
}

func rs(_ v: Double) -> String {
    let f = NumberFormatter()
    f.numberStyle = .decimal
    f.locale = Locale(identifier: "en_IN")   // 1,34,631 - the Indian grouping
    f.maximumFractionDigits = 0
    return "₹" + (f.string(from: NSNumber(value: v.rounded())) ?? "\(Int(v))")
}

func pc(_ v: Double?) -> String {
    guard let v = v else { return "–" }
    return String(format: "%@%.1f%%", v > 0 ? "+" : "", v)
}

func signed(_ n: Double) -> String {
    let r = (n * 10).rounded() / 10
    let t = r == r.rounded() ? String(Int(abs(r))) : String(format: "%.1f", abs(r))
    return r > 0 ? "+" + t : r < 0 ? "−" + t : "0"
}
func plainNum(_ n: Double) -> String { signed(n).replacingOccurrences(of: "+", with: "") }

func prettyDate(_ iso: String) -> String {
    let p = DateFormatter(); p.dateFormat = "yyyy-MM-dd"
    guard let d = p.date(from: iso) else { return iso }
    let f = DateFormatter(); f.dateFormat = "d MMM yyyy"
    return f.string(from: d)
}

func hm(_ d: Date) -> String { let f = DateFormatter(); f.dateFormat = "HH:mm"; return f.string(from: d) }

/// Menus don't wrap text, so long lines are broken by hand.
func wrap(_ text: String, _ width: Int = 64) -> String {
    text.components(separatedBy: "\n").map { para -> String in
        var lines: [String] = [], line = ""
        for word in para.split(separator: " ") {
            if line.count + word.count + 1 > width, !line.isEmpty { lines.append(line); line = "" }
            line += (line.isEmpty ? "" : " ") + word
        }
        if !line.isEmpty { lines.append(line) }
        return lines.joined(separator: "\n")
    }.joined(separator: "\n")
}

/// The agent writes "Rs 1,234"; the menu shows "₹1,234".
func rupee(_ s: String) -> String { s.replacingOccurrences(of: "Rs ", with: "₹") }

func signalColor(_ key: String) -> NSColor {
    switch key {
    case "STRONG_BUY", "BUY": return NSColor(srgbRed: 0.05, green: 0.64, blue: 0.05, alpha: 1)
    case "HOLD": return NSColor(srgbRed: 0.79, green: 0.52, blue: 0.0, alpha: 1)
    case "SELL", "STRONG_SELL": return NSColor(srgbRed: 0.82, green: 0.23, blue: 0.23, alpha: 1)
    default: return NSColor.secondaryLabelColor
    }
}

// MARK: - App

final class App: NSObject, NSApplicationDelegate, NSMenuDelegate, UNUserNotificationCenterDelegate {
    let item = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
    let dashboard = Dashboard()
    var summary: Summary?
    var live: [String: LivePrice] = [:]
    var lastError: String?
    var fetchedAt: Date?
    var timer: Timer?

    func applicationDidFinishLaunching(_ n: Notification) {
        NexusBeacon.start(name: appName) { [weak self] in
            guard let self = self else { return ("ok", "") }
            if let e = self.lastError { return ("error", e) }
            guard let s = self.summary, let it = s.items[Settings.barItem] else { return ("ok", "starting") }
            if self.isStale { return ("warn", "data is \(self.ageHours)h old") }
            return ("ok", "\(it.label) \(it.signal.label) \(rs(self.now(it)))")
        }
        Settings.applyAppearance()
        installEditMenu()
        let menu = NSMenu()
        menu.delegate = self
        item.menu = menu
        NexusBeacon.attach(item)   // lets the app live in Nexus's menu
        item.button?.toolTip = "Dharalu - wheat, gold, silver and platinum buy/sell agent"
        updateTitle()
        let center = UNUserNotificationCenter.current()
        center.delegate = self
        center.requestAuthorization(options: [.alert, .sound]) { _, _ in }
        schedule()
        refresh()
        if CommandLine.arguments.contains("--dashboard") { dashboard.show(Settings.barItem) }
    }

    func schedule() {
        timer?.invalidate()
        let t = Timer(timeInterval: TimeInterval(Settings.minutes * 60), repeats: true) { [weak self] _ in self?.refresh() }
        RunLoop.main.add(t, forMode: .common)
        timer = t
    }

    var ageHours: Int { Int((Date().timeIntervalSince(summary?.generated ?? Date())) / 3600) }
    /// The Mac job runs every 5 minutes and publishes at least hourly, so 6 hours old means it stopped.
    var isStale: Bool { summary != nil && ageHours >= 6 }
    /// Days since an item's newest price. Mandis skip Sundays and holidays; metals skip weekends.
    func priceAgeDays(_ it: Summary.Item) -> Int {
        let p = DateFormatter(); p.dateFormat = "yyyy-MM-dd"; p.timeZone = TimeZone(identifier: "Asia/Kolkata")
        guard let a = p.date(from: it.asof) else { return 0 }
        return Calendar.current.dateComponents([.day], from: a, to: Date()).day ?? 0
    }
    func pricesOld(_ it: Summary.Item) -> Bool { priceAgeDays(it) >= (it.live == nil ? 3 : 4) }

    /// Price right now: the live world price for metals (when it looks sane), else the agent's price.
    func now(_ it: Summary.Item) -> Double { live[it.key]?.rs ?? it.price }
    /// Change since the last daily close, for metals with a live price.
    func liveMove(_ it: Summary.Item) -> Double? {
        guard let l = live[it.key], let prev = it.live?.prev_close, prev > 0 else { return nil }
        return (l.rs / prev - 1) * 100
    }

    // MARK: Fetch

    @objc func refresh() {
        guard var comps = URLComponents(string: Settings.dataURL) else { lastError = "bad data URL"; updateTitle(); return }
        comps.queryItems = [URLQueryItem(name: "t", value: String(Int(Date().timeIntervalSince1970)))]   // skip caches
        URLSession.shared.dataTask(with: request(comps.url!)) { data, resp, err in
            var result: Summary?, problem: String?
            if let err = err {
                problem = err.localizedDescription
            } else if let h = resp as? HTTPURLResponse, h.statusCode != 200 {
                problem = "HTTP \(h.statusCode) from the dashboard"
            } else if let data = data {
                do { result = try JSONDecoder().decode(Summary.self, from: data) } catch { problem = "couldn't read summary.json (\(error))" }
            }
            DispatchQueue.main.async {
                if let r = result {
                    self.summary = r
                    self.lastError = nil
                    self.fetchedAt = Date()
                    self.live = self.live.filter { r.items[$0.key]?.live != nil }
                } else {
                    self.lastError = problem ?? "no data"
                }
                self.updateTitle()
                NexusBeacon.beat()
                if let r = result { self.refreshLive(r) }
            }
        }.resume()
    }

    func request(_ u: URL) -> URLRequest {
        var req = URLRequest(url: u, cachePolicy: .reloadIgnoringLocalCacheData, timeoutInterval: 30)
        req.setValue("no-cache", forHTTPHeaderField: "Cache-Control")
        return req
    }

    /// Live world prices for the metals. A tick more than 15% away from the agent's price is ignored.
    func refreshLive(_ s: Summary) {
        let group = DispatchGroup()
        var got: [String: LivePrice] = [:]
        let lock = NSLock()
        for k in s.keys {
            guard let it = s.items[k], let l = it.live, let u = URL(string: liveURL + l.symbol) else { continue }
            group.enter()
            URLSession.shared.dataTask(with: request(u)) { data, _, _ in
                defer { group.leave() }
                guard let data = data,
                      let o = (try? JSONSerialization.jsonObject(with: data)) as? [String: Any],
                      let usd = o["price"] as? Double, usd > 0 else { return }
                let price = usd * l.factor
                guard abs(price / it.price - 1) <= 0.15 else { return }
                let at = (o["updatedAt"] as? String).flatMap(isoDate) ?? Date()
                lock.lock(); got[k] = LivePrice(rs: price, at: at); lock.unlock()
            }.resume()
        }
        group.notify(queue: .main) {
            for (k, v) in got { self.live[k] = v }
            self.updateTitle()
            self.notifyIfNeeded(s)
        }
    }

    func updateTitle() {
        guard let b = item.button else { return }
        guard let s = summary, let it = s.items[Settings.barItem] ?? s.keys.first.flatMap({ s.items[$0] }) else {
            b.title = lastError == nil ? "⚖️ …" : "⚖️ ⚠︎"
            return
        }
        var t = "⚖️ \(it.emoji) \(it.signal.label)"
        if Settings.showPrice { t += " " + rs(now(it)) }
        if isStale || lastError != nil { t += " ⚠︎" }
        b.title = t
    }

    // MARK: Notifications

    /// Per commodity: tell when the call changes, and once a day when the price moves a lot.
    func notifyIfNeeded(_ s: Summary) {
        for k in s.keys {
            guard let it = s.items[k] else { continue }
            let sig = it.signal
            defer { Settings.setLastSignal(k, sig.key) }
            guard Settings.notify else { continue }
            if let prev = Settings.lastSignal(k), prev != sig.key {
                post(id: "signal-\(k)-\(it.asof)-\(sig.key)", key: k,
                     title: "Dharalu: \(it.emoji) \(it.label) now \(sig.label) · \(sig.telugu)",
                     body: "Was \(prev.replacingOccurrences(of: "_", with: " ")). Score \(signed(sig.score)) of ±\(plainNum(sig.max_score)), confidence \(sig.confidence). \(sig.plain.map { $0 + " " } ?? "")If buying: \(sig.buyer) If holding: \(sig.holder)")
            }
            let limit = it.move_alert_pct ?? 2.5
            let move = liveMove(it) ?? it.chg_1d
            let day = live[k] != nil ? dayStamp() : it.asof
            if let m = move, abs(m) >= limit, Settings.lastMove(k) != day {
                Settings.setLastMove(k, day)
                post(id: "move-\(k)-\(day)", key: k,
                     title: "Dharalu: \(it.emoji) \(it.label) \(m > 0 ? "up" : "down") \(pc(m)) today",
                     body: "\(rs(now(it)))\(it.unit_short)\(live[k] != nil ? " (live)" : " on \(prettyDate(it.asof))"). Call: \(sig.label).")
            }
        }
    }

    func dayStamp() -> String {
        let f = DateFormatter(); f.dateFormat = "yyyy-MM-dd"; f.timeZone = TimeZone(identifier: "Asia/Kolkata")
        return f.string(from: Date())
    }

    func post(id: String, key: String, title: String, body: String) {
        let c = UNMutableNotificationContent()
        c.title = title
        c.body = body
        c.sound = .default
        c.userInfo = ["key": key]
        UNUserNotificationCenter.current().add(UNNotificationRequest(identifier: id, content: c, trigger: nil))
    }

    func userNotificationCenter(_ c: UNUserNotificationCenter, willPresent n: UNNotification,
                                withCompletionHandler done: @escaping (UNNotificationPresentationOptions) -> Void) {
        done([.banner, .sound])
    }

    func userNotificationCenter(_ c: UNUserNotificationCenter, didReceive r: UNNotificationResponse,
                                withCompletionHandler done: @escaping () -> Void) {
        dashboard.show(r.notification.request.content.userInfo["key"] as? String ?? Settings.barItem)
        done()
    }

    // MARK: Menu

    func menuNeedsUpdate(_ menu: NSMenu) {
        menu.removeAllItems()
        if let s = summary {
            for k in s.keys { if let it = s.items[k] { menu.addItem(commodityRow(it)) } }
        } else {
            menu.addItem(info(lastError.map { "Couldn't load today's calls: \($0)" } ?? "Loading today's calls…"))
        }
        if let e = lastError, summary != nil { menu.addItem(info(wrap("⚠︎ Last refresh failed: \(e) - showing the previous data."))) }
        if isStale {
            menu.addItem(info(wrap("⚠︎ This data is \(ageHours) hours old. The Mac refresh job may have stopped - on the Mac with the repo, run scripts/mac-schedule.sh status.")))
        }
        menu.addItem(.separator())
        menu.addItem(action("Open Dashboard…", #selector(openDashboard), "d"))
        menu.addItem(action("Open in Browser", #selector(openBrowser)))
        menu.addItem(action("Refresh Now", #selector(refresh), "r"))
        if let f = fetchedAt {
            let fmt = DateFormatter(); fmt.dateFormat = "d MMM, HH:mm"
            let gen = summary?.generated.map { fmt.string(from: $0) } ?? "?"
            menu.addItem(info("Checked \(fmt.string(from: f)) · agent ran \(gen) · every \(Settings.minutes) min"))
        }
        menu.addItem(.separator())
        menu.addItem(settingsItem())
        menu.addItem(action("Help - How to Use", #selector(openHelp)))
        menu.addItem(action("Quit Dharalu", #selector(quit), "q"))
    }

    /// One line per commodity ("🥇 Gold  STRONG SELL  ₹1,34,631/10 g  +0.4%"), the full call in its submenu.
    func commodityRow(_ it: Summary.Item) -> NSMenuItem {
        let row = NSMenuItem(title: it.label, action: nil, keyEquivalent: "")
        let t = NSMutableAttributedString(string: "\(it.emoji)  \(it.label)   ", attributes: [.font: NSFont.menuFont(ofSize: 14)])
        t.append(NSAttributedString(string: it.signal.label, attributes: [.font: NSFont.boldSystemFont(ofSize: 14), .foregroundColor: signalColor(it.signal.key)]))
        t.append(NSAttributedString(string: "   \(rs(now(it)))\(it.unit_short)", attributes: [.font: NSFont.monospacedDigitSystemFont(ofSize: 14, weight: .regular)]))
        let move = liveMove(it) ?? it.chg_1d
        t.append(NSAttributedString(string: "  \(pc(move))\(live[it.key] != nil ? " ●" : "")",
                                    attributes: [.font: NSFont.monospacedDigitSystemFont(ofSize: 12, weight: .regular),
                                                 .foregroundColor: (move ?? 0) > 0 ? signalColor("BUY") : (move ?? 0) < 0 ? signalColor("SELL") : NSColor.secondaryLabelColor]))
        row.attributedTitle = t
        if it.key == Settings.barItem { row.state = .on }
        row.submenu = detailMenu(it)
        return row
    }

    func detailMenu(_ it: Summary.Item) -> NSMenu {
        let menu = NSMenu()
        let s = it.signal
        let head = NSMenuItem()
        let t = NSMutableAttributedString(string: "\(it.emoji) \(it.label)\(it.telugu_name.map { " · \($0)" } ?? "") - \(s.label) · \(s.telugu)\n",
                                          attributes: [.font: NSFont.boldSystemFont(ofSize: 15), .foregroundColor: signalColor(s.key)])
        t.append(NSAttributedString(string: "Score \(signed(s.score)) of ±\(plainNum(s.max_score)) · confidence \(s.confidence) · \(prettyDate(it.asof))",
                                    attributes: [.font: NSFont.menuFont(ofSize: 12), .foregroundColor: NSColor.secondaryLabelColor]))
        head.attributedTitle = t
        head.isEnabled = false
        menu.addItem(head)
        if let p = s.plain { menu.addItem(info(wrap(p, 70))) }
        if let p = s.pending { menu.addItem(info(wrap("⏳ " + p, 70))) }
        menu.addItem(info(wrap("If buying: \(s.buyer)")))
        menu.addItem(info(wrap("If holding: \(s.holder)")))
        if let c = s.change_line { menu.addItem(info(wrap("🎯 " + rupee(c), 70))) }
        if let r = s.record_line { menu.addItem(info(wrap("📊 " + r, 70))) }
        if let w = s.confidence_why, !w.isEmpty { menu.addItem(info(wrap("🤔 \(s.confidence) confidence: " + w.joined(separator: " · "), 70))) }
        if let c = it.changes, c.call_changed == true, let was = c.label_was {
            menu.addItem(info("🔄 Was \(was) on \(prettyDate(c.since))"))
        }
        if let l = it.long_term {
            menu.addItem(info(wrap("📅 Saving for years: \(l.label) - \(l.advice)", 70)))
        }
        menu.addItem(.separator())

        if let l = live[it.key] {
            menu.addItem(info("Live \(rs(l.rs))\(it.unit_short) at \(hm(l.at)) · since last close \(pc(liveMove(it)))"))
            menu.addItem(info("Agent's price \(rs(it.price)) on \(prettyDate(it.asof)) · 7d \(pc(it.chg_7d)) · 30d \(pc(it.chg_30d))"))
        } else {
            menu.addItem(info("Price \(rs(it.price))\(it.unit_short) on \(prettyDate(it.asof)) · 1d \(pc(it.chg_1d)) · 7d \(pc(it.chg_7d)) · 30d \(pc(it.chg_30d))"))
        }
        let pk = summary?.place?.key ?? Settings.place
        if let w = it.where_by_place?[pk] ?? it.where {
            let row = info(wrap("📍 \(w.short)", 70))
            row.toolTip = w.detail
            menu.addItem(row)
            if let n = w.place_note { menu.addItem(info(wrap("📍 \(n)", 70))) }
        }
        if let f = it.forecast30 {
            menu.addItem(info("30-day forecast \(rs(f.price)) (likely \(rs(f.low)) – \(rs(f.high)))"))
            if let why = it.forecast_why?.summary { menu.addItem(info(wrap("🔮 Why: \(why)", 70))) }
        }
        for line in it.lines_by_place?[pk] ?? it.lines ?? [] { menu.addItem(info(wrap(rupee(line), 70))) }
        if let cc = it.carrying_cost_30d_pct { menu.addItem(info("Holding cost \(String(format: "%.1f", cc))% per 30 days")) }
        if pricesOld(it) {
            menu.addItem(info(wrap("⚠︎ The newest price is from \(prettyDate(it.asof)) (\(priceAgeDays(it)) days ago)." +
                                   (it.live == nil ? " data.gov.in may not be giving new prices - run scripts/mac-refresh.sh on the Mac." : ""))))
        }
        menu.addItem(.separator())

        // The proof: every rule, its number, the test and the points it gave.
        let proof = NSMenuItem(title: "Why this call - the proof", action: nil, keyEquivalent: "")
        let pm = NSMenu()
        for e in it.evidence {
            let row = NSMenuItem()
            let c = e.counted ?? e.points
            let w = e.weight.map { " ×\(plainNum($0)) = \(signed(c))" } ?? ""
            let a = NSMutableAttributedString(string: "\(signed(e.points))\(w)   \(e.rule)\n",
                                              attributes: [.font: NSFont.boldSystemFont(ofSize: 13),
                                                           .foregroundColor: c > 0 ? signalColor("BUY") : c < 0 ? signalColor("SELL") : NSColor.labelColor])
            a.append(NSAttributedString(string: wrap(rupee(e.value), 70) + "\n",
                                        attributes: [.font: NSFont.menuFont(ofSize: 12), .foregroundColor: NSColor.labelColor]))
            a.append(NSAttributedString(string: wrap("Test: \(e.test)", 80) + "\n" + wrap("Source: \(e.source)", 80),
                                        attributes: [.font: NSFont.menuFont(ofSize: 11), .foregroundColor: NSColor.secondaryLabelColor]))
            row.attributedTitle = a
            row.toolTip = e.why
            row.isEnabled = false
            pm.addItem(row)
        }
        pm.addItem(.separator())
        if let cap = s.trend_cap { pm.addItem(info(wrap("🧢 " + cap, 80))) }
        pm.addItem(info("Total score \(signed(s.score)) → \(s.label)   (≥+3 strong buy · +1 to +3 buy · between −1 and +1 hold/wait · −1 to −3 sell · ≤−3 strong sell)"))
        pm.addItem(info("Points × weight (learned from each rule's own record) = counted"))
        if let q = s.equal, q.key != s.key { pm.addItem(info("Every rule counting the same would say \(q.label) (\(signed(q.score)))")) }
        proof.submenu = pm
        menu.addItem(proof)

        let rec = NSMenuItem(title: "Has this worked before?", action: nil, keyEquivalent: "")
        let rm = NSMenu()
        if let g = it.record?.same_call {
            let word = s.label
            if s.key == "HOLD", let beat = g.beat_holding_cost_pct {
                rm.addItem(info("HOLD days (\(g.days), \(g.scope ?? "last year")): keeping beat the holding cost \(String(format: "%.0f", beat))% of the time, avg \(pc(g.avg_move_pct))"))
            } else {
                let falling = s.key.contains("SELL")
                let hit = falling ? 100 - g.rose_pct : g.rose_pct
                rm.addItem(info("\(word) days (\(g.days), \(g.scope ?? "last year")): price \(falling ? "lower" : "higher") 30 days later \(String(format: "%.0f", hit))% of the time, avg \(pc(g.avg_move_pct))"))
            }
        } else {
            rm.addItem(info("Not enough past days with this call yet."))
        }
        if let r = it.record {
            rm.addItem(.separator())
            rm.addItem(info((r.live_graded ?? 0) > 0
                ? "Live calls: \(r.live_graded!) graded, right \(String(format: "%.0f", r.live_right_pct ?? 0))% of the time"
                : "Live calls are graded 30 days after each one"))
        }
        rm.addItem(info("Replayed day by day using only the data known each day."))
        rm.addItem(action("Open the full track record…", #selector(openPage(_:)), represented: "\(it.key)/record"))
        rec.submenu = rm
        menu.addItem(rec)

        let br = NSMenuItem(title: "Today's briefing", action: nil, keyEquivalent: "")
        let bm = NSMenu()
        bm.addItem(info(wrap(rupee(it.briefing.english), 80)))
        bm.addItem(.separator())
        bm.addItem(info(wrap(rupee(it.briefing.telugu), 70)))
        bm.addItem(.separator())
        bm.addItem(action("Copy English", #selector(copyEnglish(_:)), represented: it.key))
        bm.addItem(action("Copy తెలుగు", #selector(copyTelugu(_:)), represented: it.key))
        br.submenu = bm
        menu.addItem(br)

        if let tm = it.timing {
            let days = tm.days_to_buy_window ?? 0
            menu.addItem(info("Usually cheapest \(tm.cheapest_months.joined(separator: " & ")) · dearest \(tm.dearest_months.joined(separator: " & "))"
                              + (days > 0 ? " · buy window in \(days) days" : " · in the buy window now")))
        }
        menu.addItem(.separator())
        menu.addItem(action("Open \(it.label) in Dashboard…", #selector(openPage(_:)), represented: "\(it.key)/today"))
        menu.addItem(action("Timeline - past, now, forecast…", #selector(openPage(_:)), represented: "\(it.key)/timeline"))
        if it.key != Settings.barItem {
            menu.addItem(action("Show \(it.label) in the Menu Bar", #selector(pickBar(_:)), represented: it.key))
        }
        return menu
    }

    func settingsItem() -> NSMenuItem {
        let it = NSMenuItem(title: "Settings", action: nil, keyEquivalent: "")
        let m = NSMenu()
        // Menu bar
        m.addItem(groupHeader("Menu bar"))
        m.addItem(segmentRow("Show", ["🌾 Wheat", "🥇 Gold", "🥈 Silver", "💠 Plat."], defaultOrder.firstIndex(of: Settings.barItem) ?? 0, #selector(segBar(_:))))
        m.addItem(switchRow("Show price", Settings.showPrice, #selector(switchPrice(_:))))
        // Place
        m.addItem(.separator())
        m.addItem(groupHeader("Place"))
        let ps = placeChoices
        m.addItem(segmentRow("📍 Wheat landed cost & margins for", ps.map { $0.name },
                             ps.firstIndex { $0.key == (summary?.place?.key ?? Settings.place) } ?? 0, #selector(segPlace(_:))))
        // Alerts
        m.addItem(.separator())
        m.addItem(groupHeader("Alerts"))
        m.addItem(switchRow("Notify on call changes / big moves", Settings.notify, #selector(switchNotify(_:))))
        m.addItem(segmentRow("Check prices every", Settings.minuteOptions.map { $0 < 60 ? "\($0)m" : "\($0 / 60)h" },
                             Settings.minuteOptions.firstIndex(of: Settings.minutes) ?? 0, #selector(segMinutes(_:))))
        // General
        m.addItem(.separator())
        m.addItem(groupHeader("General"))
        m.addItem(switchRow("Launch at login", SMAppService.mainApp.status == .enabled, #selector(switchLogin(_:))))
        m.addItem(segmentRow("Appearance", ["System", "Light", "Dark"], ["system", "light", "dark"].firstIndex(of: Settings.appearance) ?? 0, #selector(segAppearance(_:))))
        m.addItem(.separator())
        m.addItem(action("Data Source…", #selector(editSource)))
        it.submenu = m
        return it
    }

    // MARK: Settings rows (grouped, with switches and segmented controls)

    static let rowWidth: CGFloat = 320

    func groupHeader(_ title: String) -> NSMenuItem {
        let it = NSMenuItem()
        it.isEnabled = false
        it.attributedTitle = NSAttributedString(string: title.uppercased(), attributes: [
            .font: NSFont.systemFont(ofSize: 10, weight: .semibold),
            .foregroundColor: NSColor.secondaryLabelColor,
            .kern: 0.6])
        return it
    }

    func rowLabel(_ text: String) -> NSTextField {
        let l = NSTextField(labelWithString: text)
        l.font = .menuFont(ofSize: 13)
        l.textColor = .labelColor
        l.lineBreakMode = .byTruncatingTail
        return l
    }

    func switchRow(_ title: String, _ on: Bool, _ sel: Selector) -> NSMenuItem {
        let v = NSView(frame: NSRect(x: 0, y: 0, width: App.rowWidth, height: 30))
        let l = rowLabel(title); l.frame = NSRect(x: 14, y: 6, width: App.rowWidth - 82, height: 18)
        let sw = NSSwitch(); sw.controlSize = .small; sw.state = on ? .on : .off
        sw.target = self; sw.action = sel
        sw.sizeToFit(); sw.frame.origin = NSPoint(x: App.rowWidth - sw.frame.width - 14, y: (30 - sw.frame.height) / 2)
        v.addSubview(l); v.addSubview(sw)
        let it = NSMenuItem(); it.view = v
        return it
    }

    func segmentRow(_ title: String, _ labels: [String], _ selected: Int, _ sel: Selector) -> NSMenuItem {
        let v = NSView(frame: NSRect(x: 0, y: 0, width: App.rowWidth, height: 52))
        let l = rowLabel(title); l.frame = NSRect(x: 14, y: 31, width: App.rowWidth - 28, height: 16)
        let seg = NSSegmentedControl(labels: labels, trackingMode: .selectOne, target: self, action: sel)
        seg.controlSize = .small; seg.segmentStyle = .rounded; seg.selectedSegment = selected
        seg.frame = NSRect(x: 14, y: 5, width: App.rowWidth - 28, height: 22)
        v.addSubview(l); v.addSubview(seg)
        let it = NSMenuItem(); it.view = v
        return it
    }

    @objc func segBar(_ s: NSSegmentedControl) {
        guard defaultOrder.indices.contains(s.selectedSegment) else { return }
        Settings.barItem = defaultOrder[s.selectedSegment]; updateTitle()
    }
    @objc func pickBar(_ m: NSMenuItem) {
        guard let k = m.representedObject as? String else { return }
        Settings.barItem = k; updateTitle()
    }
    /// From summary.json; the two built-in places until the first load.
    var placeChoices: [Summary.Place] {
        summary?.places ?? [Summary.Place(key: "srikakulam", name: "Srikakulam", state: "Andhra Pradesh", telugu: nil, default: true),
                            Summary.Place(key: "hyderabad", name: "Hyderabad", state: "Telangana", telugu: nil, default: false)]
    }
    @objc func segPlace(_ s: NSSegmentedControl) {
        let ps = placeChoices
        guard ps.indices.contains(s.selectedSegment) else { return }
        Settings.place = ps[s.selectedSegment].key
        dashboard.applyPlace()
    }
    @objc func switchPrice(_ s: NSSwitch) { Settings.showPrice = s.state == .on; updateTitle() }
    @objc func switchNotify(_ s: NSSwitch) { Settings.notify = s.state == .on }
    @objc func switchLogin(_ s: NSSwitch) {
        toggleLogin()
        s.state = SMAppService.mainApp.status == .enabled ? .on : .off   // snap back if it failed
    }
    @objc func segMinutes(_ s: NSSegmentedControl) {
        let opts = Settings.minuteOptions
        guard opts.indices.contains(s.selectedSegment) else { return }
        Settings.minutes = opts[s.selectedSegment]; schedule()
    }
    @objc func segAppearance(_ s: NSSegmentedControl) {
        let opts = ["system", "light", "dark"]
        guard opts.indices.contains(s.selectedSegment) else { return }
        Settings.appearance = opts[s.selectedSegment]
        Settings.applyAppearance()
        dashboard.applyTheme()
    }

    func info(_ title: String) -> NSMenuItem {
        let it = NSMenuItem(title: title, action: nil, keyEquivalent: "")
        it.isEnabled = false
        return it
    }

    func action(_ title: String, _ sel: Selector, _ key: String = "", represented: Any? = nil) -> NSMenuItem {
        let it = NSMenuItem(title: title, action: sel, keyEquivalent: key)
        it.target = self
        it.representedObject = represented
        return it
    }

    // MARK: Actions

    @objc func openDashboard() { dashboard.show("all") }
    @objc func openPage(_ m: NSMenuItem) { dashboard.show(m.representedObject as? String ?? "all") }
    @objc func openBrowser() { NSWorkspace.shared.open(Settings.siteURL) }
    @objc func openHelp() { NSWorkspace.shared.open(URL(string: repoURL + "/blob/main/guide/MAC_APP.md")!) }
    @objc func quit() { NSApp.terminate(nil) }

    @objc func copyEnglish(_ m: NSMenuItem) { copy(m, \.english) }
    @objc func copyTelugu(_ m: NSMenuItem) { copy(m, \.telugu) }
    func copy(_ m: NSMenuItem, _ path: KeyPath<Summary.Briefing, String>) {
        guard let k = m.representedObject as? String, let it = summary?.items[k] else { return }
        NSPasteboard.general.clearContents()
        NSPasteboard.general.setString(rupee(it.briefing[keyPath: path]) + "\n" + Settings.pageURL("\(k)/today").absoluteString, forType: .string)
    }

    @objc func toggleLogin() {
        do {
            if SMAppService.mainApp.status == .enabled { try SMAppService.mainApp.unregister() }
            else { try SMAppService.mainApp.register() }
        } catch {
            let a = NSAlert()
            a.messageText = "Couldn't change Launch at Login"
            a.informativeText = "\(error.localizedDescription)\n\nMove Dharalu to the Applications folder and try again, or add it in System Settings → General → Login Items."
            a.runModal()
        }
    }

    @objc func editSource() {
        let a = NSAlert()
        a.messageText = "Data source"
        a.informativeText = "The summary.json your Dharalu dashboard publishes. Change it only if you run your own copy (fork) of the repo."
        let f = NSTextField(frame: NSRect(x: 0, y: 0, width: 420, height: 24))
        f.stringValue = Settings.dataURL
        a.accessoryView = f
        a.addButton(withTitle: "Save")
        a.addButton(withTitle: "Cancel")
        a.addButton(withTitle: "Reset to Default")
        NSApp.activate(ignoringOtherApps: true)
        switch a.runModal() {
        case .alertFirstButtonReturn: Settings.dataURL = f.stringValue.trimmingCharacters(in: .whitespaces)
        case .alertThirdButtonReturn: Settings.d.removeObject(forKey: "dataURL")
        default: return
        }
        for k in defaultOrder { Settings.setLastSignal(k, nil) }   // a different source shouldn't count as a call change
        summary = nil
        live = [:]
        refresh()
    }

    /// Menu-bar apps have no main menu, so ⌘C / ⌘V would not work in the dashboard's text fields.
    func installEditMenu() {
        let main = NSMenu()
        let appItem = NSMenuItem(); main.addItem(appItem)
        let am = NSMenu(); am.addItem(withTitle: "Close Window", action: #selector(NSWindow.performClose(_:)), keyEquivalent: "w")
        appItem.submenu = am
        let editItem = NSMenuItem(); main.addItem(editItem)
        let em = NSMenu(title: "Edit")
        em.addItem(withTitle: "Undo", action: Selector(("undo:")), keyEquivalent: "z")
        em.addItem(withTitle: "Redo", action: Selector(("redo:")), keyEquivalent: "Z")
        em.addItem(.separator())
        em.addItem(withTitle: "Cut", action: #selector(NSText.cut(_:)), keyEquivalent: "x")
        em.addItem(withTitle: "Copy", action: #selector(NSText.copy(_:)), keyEquivalent: "c")
        em.addItem(withTitle: "Paste", action: #selector(NSText.paste(_:)), keyEquivalent: "v")
        em.addItem(withTitle: "Select All", action: #selector(NSText.selectAll(_:)), keyEquivalent: "a")
        editItem.submenu = em
        NSApp.mainMenu = main
    }
}

// MARK: - Dashboard window

/// The full dashboard in a window. Trades you enter here are kept in this app's own
/// web storage (separate from your browser) - use Export CSV / Import CSV to move them.
final class Dashboard: NSObject, NSWindowDelegate, WKNavigationDelegate, WKUIDelegate, WKDownloadDelegate, WKScriptMessageHandler {
    var window: NSWindow?
    var web: WKWebView?

    /// Opens the dashboard at a page, e.g. "all", "gold/today" or "silver/timeline".
    func show(_ hash: String) {
        let target = Settings.pageURL(hash.contains("/") || hash == "all" ? hash : "\(hash)/today")
        if window == nil {
            let cfg = WKWebViewConfiguration()
            cfg.websiteDataStore = .default()   // keeps trades (localStorage) between launches
            // Apply the Appearance and Place choices before the page's own script reads them.
            Dashboard.addScripts(cfg.userContentController)
            // The page's 📍 picklist tells the app, so Settings › Place and the menu follow it.
            cfg.userContentController.add(self, name: "dharaluPlace")
            let w = WKWebView(frame: .zero, configuration: cfg)
            w.navigationDelegate = self
            w.uiDelegate = self
            w.allowsBackForwardNavigationGestures = true
            let win = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 1240, height: 860),
                               styleMask: [.titled, .closable, .miniaturizable, .resizable], backing: .buffered, defer: false)
            win.title = "Dharalu · ధరలు"
            win.contentView = w
            win.isReleasedWhenClosed = false
            win.delegate = self
            win.setFrameAutosaveName("DharaluDashboard")
            if !win.setFrameUsingName("DharaluDashboard") { win.center() }
            window = win
            web = w
            w.load(URLRequest(url: target))
        } else if web?.url?.host != Settings.siteURL.host {
            web?.load(URLRequest(url: target))
        } else {
            // Same page: switch the hash (the page re-routes and re-polls) instead of a full reload.
            let h = target.fragment ?? "all"
            web?.evaluateJavaScript("location.hash='\(h)';", completionHandler: nil)
        }
        NSApp.setActivationPolicy(.regular)   // Dock icon + ⌘-Tab while the window is open
        NSApp.activate(ignoringOtherApps: true)
        window?.makeKeyAndOrderFront(nil)
    }

    /// Re-theme the open page at once (the script is re-read on every load, so it is always current).
    func applyTheme() {
        guard let w = web else { return }
        Dashboard.addScripts(w.configuration.userContentController)
        w.evaluateJavaScript(Settings.themeScript + ";if(typeof renderAll==='function'){try{renderAll()}catch(e){}}", completionHandler: nil)
    }

    static func addScripts(_ u: WKUserContentController) {
        u.removeAllUserScripts()
        u.addUserScript(WKUserScript(source: Settings.themeScript + Settings.placeScript, injectionTime: .atDocumentStart, forMainFrameOnly: true))
    }

    /// Switch the open page to the place picked in Settings.
    func applyPlace() {
        guard let w = web else { return }
        Dashboard.addScripts(w.configuration.userContentController)
        w.evaluateJavaScript(Settings.placeScript + ";if(typeof setPlace==='function'){try{setPlace(JSON.parse(localStorage.getItem('dh.place')))}catch(e){}}", completionHandler: nil)
    }

    func userContentController(_ u: WKUserContentController, didReceive m: WKScriptMessage) {
        if m.name == "dharaluPlace", let k = m.body as? String, !k.isEmpty { Settings.place = k }
    }

    func windowWillClose(_ n: Notification) { NSApp.setActivationPolicy(.accessory) }

    // Links that leave the dashboard (Help, GitHub, pib.gov.in…) open in the browser.
    func webView(_ w: WKWebView, decidePolicyFor a: WKNavigationAction, decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
        if a.shouldPerformDownload { decisionHandler(.download); return }
        if let u = a.request.url, a.navigationType == .linkActivated, u.host != Settings.siteURL.host {
            NSWorkspace.shared.open(u)
            decisionHandler(.cancel)
            return
        }
        decisionHandler(.allow)
    }

    func webView(_ w: WKWebView, createWebViewWith c: WKWebViewConfiguration, for a: WKNavigationAction,
                 windowFeatures f: WKWindowFeatures) -> WKWebView? {
        if let u = a.request.url { NSWorkspace.shared.open(u) }   // target="_blank"
        return nil
    }

    func webView(_ w: WKWebView, navigationAction: WKNavigationAction, didBecome d: WKDownload) { d.delegate = self }
    func webView(_ w: WKWebView, navigationResponse: WKNavigationResponse, didBecome d: WKDownload) { d.delegate = self }

    // Export CSV
    func download(_ d: WKDownload, decideDestinationUsing r: URLResponse, suggestedFilename name: String,
                  completionHandler done: @escaping (URL?) -> Void) {
        let p = NSSavePanel()
        p.nameFieldStringValue = name
        p.directoryURL = FileManager.default.urls(for: .downloadsDirectory, in: .userDomainMask).first
        guard let win = window else { done(nil); return }
        p.beginSheetModal(for: win) { r in
            guard r == .OK, let u = p.url else { done(nil); return }
            try? FileManager.default.removeItem(at: u)
            done(u)
        }
    }

    // Import CSV
    func webView(_ w: WKWebView, runOpenPanelWith p: WKOpenPanelParameters, initiatedByFrame f: WKFrameInfo,
                 completionHandler done: @escaping ([URL]?) -> Void) {
        let o = NSOpenPanel()
        o.allowsMultipleSelection = p.allowsMultipleSelection
        o.canChooseDirectories = false
        guard let win = window else { done(nil); return }
        o.beginSheetModal(for: win) { r in done(r == .OK ? o.urls : nil) }
    }

    // alert() / confirm() from the page
    func webView(_ w: WKWebView, runJavaScriptAlertPanelWithMessage m: String, initiatedByFrame f: WKFrameInfo,
                 completionHandler done: @escaping () -> Void) {
        let a = NSAlert(); a.messageText = m
        a.runModal(); done()
    }

    func webView(_ w: WKWebView, runJavaScriptConfirmPanelWithMessage m: String, initiatedByFrame f: WKFrameInfo,
                 completionHandler done: @escaping (Bool) -> Void) {
        let a = NSAlert(); a.messageText = m
        a.addButton(withTitle: "OK"); a.addButton(withTitle: "Cancel")
        done(a.runModal() == .alertFirstButtonReturn)
    }
}

// MARK: - Main

let app = NSApplication.shared
let delegate = App()
app.delegate = delegate
app.setActivationPolicy(.accessory)
app.run()
