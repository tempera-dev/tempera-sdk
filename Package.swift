// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "TemperaMerchantSDK",
    platforms: [.iOS(.v17), .macOS(.v13)],
    products: [
        .library(name: "TemperaMerchantSDK", targets: ["TemperaMerchantSDK"]),
        // The generated full-surface SDK: every product and every typed
        // operation in surface.json, with no hand-written per-product wrapper.
        .library(name: "TemperaSDK", targets: ["TemperaSDK"]),
        .executable(name: "merchant-onboarding-example", targets: ["MerchantOnboardingExample"]),
    ],
    targets: [
        .target(name: "TemperaMerchantSDK", path: "packages/swift/Sources/TemperaMerchantSDK"),
        .target(name: "TemperaSDK", path: "packages/swift/Sources/TemperaSDK"),
        .executableTarget(
            name: "MerchantOnboardingExample",
            dependencies: ["TemperaMerchantSDK"],
            path: "packages/swift/Sources/MerchantOnboardingExample"
        ),
        .testTarget(
            name: "TemperaMerchantSDKTests",
            dependencies: ["TemperaMerchantSDK"],
            path: "packages/swift/Tests/TemperaMerchantSDKTests",
            resources: [.copy("Fixtures")]
        ),
        .testTarget(
            name: "TemperaSDKTests",
            dependencies: ["TemperaSDK"],
            path: "packages/swift/Tests/TemperaSDKTests"
        ),
    ]
)
