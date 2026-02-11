import Flutter
import UIKit
import GoogleMaps

@main
@objc class AppDelegate: FlutterAppDelegate {
  override func application(
    _ application: UIApplication,
    didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?
  ) -> Bool {
    // TODO: Replace with your actual Google Maps API Key
    let controller = FlutterViewController.init(project: nil, nibName: nil, bundle: nil)
    // Read API Key from Info.plist (injected via Config.xcconfig)
    if let apiKey = Bundle.main.object(forInfoDictionaryKey: "GoogleMapsAPIKey") as? String {
        GMSServices.provideAPIKey(apiKey)
    }
    GeneratedPluginRegistrant.register(with: self)
    return super.application(application, didFinishLaunchingWithOptions: launchOptions)
  }
}
