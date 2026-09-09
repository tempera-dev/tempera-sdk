pluginManagement {
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
    }
}
dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()
        maven {
            url = uri(providers.gradleProperty("fixtureRepository").getOrElse(file("build/fixture-repository").absolutePath))
        }
    }
}

rootProject.name = "tempera-sdk-kotlin-android"
include(":fixture-app")
