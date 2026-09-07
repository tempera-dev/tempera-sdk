// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "TemperaMerchantSDK",
    platforms: [.iOS(.v17), .macOS(.v13)],
    products: [
        .library(name: "TemperaMerchantSDK", targets: ["TemperaMerchantSDK"]),
        .executable(name: "merchant-onboarding-example", targets: ["MerchantOnboardingExample"]),
    ],
    targets: [
        .target(name: "TemperaMerchantSDK", path: "packages/swift/Sources/TemperaMerchantSDK"),
        .executableTarget(
            name: "MerchantOnboardingExample",
            dependencies: ["TemperaMerchantSDK"],
            path: "packages/swift/Sources/MerchantOnboardingExample"
        ),
        .testTarget(
            name: "TemperaMerchantSDKTests",
            dependencies: ["TemperaMerchantSDK"],
            path: "packages/swift/Tests/TemperaMerchantSDKTests"
        ),
    ]
)
