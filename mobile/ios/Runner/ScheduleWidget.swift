import WidgetKit
import SwiftUI

struct Provider: TimelineProvider {
    func placeholder(in context: Context) -> SimpleEntry {
        SimpleEntry(date: Date(), title: "下一場行程", content: "載入中...")
    }

    func getSnapshot(in context: Context, completion: @escaping (SimpleEntry) -> ()) {
        let entry = readEntry()
        completion(entry)
    }

    func getTimeline(in context: Context, completion: @escaping (Timeline<Entry>) -> ()) {
        let entry = readEntry()
        let timeline = Timeline(entries: [entry], policy: .atEnd)
        completion(timeline)
    }
    
    private func readEntry() -> SimpleEntry {
        let userDefaults = UserDefaults(suiteName: "group.com.example.schedule_management")
        let title = userDefaults?.string(forKey: "title") ?? "無行程"
        let content = userDefaults?.string(forKey: "content") ?? "點擊打開 App"
        return SimpleEntry(date: Date(), title: title, content: content)
    }
}

struct SimpleEntry: TimelineEntry {
    let date: Date
    let title: String
    let content: String
}

struct ScheduleWidgetEntryView : View {
    var entry: Provider.Entry

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack {
                Text("📍 下一場行程")
                    .font(.caption2)
                    .foregroundColor(.blue)
                Spacer()
                // 加入一個快速跳轉按鈕
                Link(destination: URL(string: "scheduleapp://add")!) {
                    Image(systemName: "plus.circle.fill")
                        .foregroundColor(.blue)
                        .font(.title2)
                }
            }
            
            VStack(alignment: .leading, spacing: 4) {
                Text(entry.title)
                    .font(.headline)
                Text(entry.content)
                    .font(.subheadline)
                    .foregroundColor(.secondary)
            }
        }
        .padding()
        // 點擊整個 Widget 也會跳轉
        .widgetURL(URL(string: "scheduleapp://home"))
    }
}

@main
struct ScheduleWidget: Widget {
    let kind: String = "ScheduleWidget"

    var body: some WidgetConfiguration {
        StaticConfiguration(kind: kind, provider: Provider()) { entry in
            ScheduleWidgetEntryView(entry: entry)
        }
        .configurationDisplayName("行程紀錄小工具")
        .description("快速查看下一場預定行程。")
        .supportedFamilies([.systemSmall, .systemMedium])
    }
}
