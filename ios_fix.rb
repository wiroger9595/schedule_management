require 'xcodeproj'

project_path = 'mobile/ios/Runner.xcodeproj'
project = Xcodeproj::Project.open(project_path)

# 1. 找到 Runner Target
target = project.targets.find { |t| t.name == 'Runner' }

if target
  puts "正在修復 Target: #{target.name}..."

  # 2. 關閉 User Script Sandboxing
  target.build_configurations.each do |config|
    config.build_settings['ENABLE_USER_SCRIPT_SANDBOXING'] = 'NO'
    puts "已將 #{config.name} 的 ENABLE_USER_SCRIPT_SANDBOXING 設為 NO"
  end

  # 3. 調整 Build Phases 順序
  # 我們要找的關鍵 Phase 名稱
  embed_extensions = target.build_phases.find { |p| p.display_name.include?('Embed App Extensions') }
  thin_binary = target.build_phases.find { |p| p.display_name.include?('Thin Binary') }
  embed_pods = target.build_phases.find { |p| p.display_name.include?('[CP] Embed Pods Frameworks') }

  if embed_extensions && thin_binary
    # 移除並重新插入
    target.build_phases.delete(embed_extensions)
    target.build_phases.delete(thin_binary)

    # 將 Embed Extensions 插到前面 (索引 1 或 2)
    target.build_phases.insert(1, embed_extensions)
    # 將 Thin Binary 插到最後面
    target.build_phases.push(thin_binary)

    puts "已重排 Build Phases 順序 (Embed Extensions 提前, Thin Binary 最後)"
  end

  project.save
  puts "✅ 修復完成！請執行 flutter run"
else
  puts "❌ 找不到 Runner Target，請確認路徑是否正確"
end
