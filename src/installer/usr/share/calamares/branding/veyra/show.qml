/* VeyraOS installation slideshow (Calamares slideshow API 2). */
import QtQuick 2.15
import calamares.slideshow 1.0

Presentation {
    id: presentation

    function nextSlide() { presentation.goToNextSlide() }

    Timer {
        id: advanceTimer
        interval: 9000
        running: presentation.activatedInCalamares
        repeat: true
        onTriggered: nextSlide()
    }

    component VeyraSlide: Slide {
        property string heading
        property string body
        Image {
            anchors.fill: parent
            source: "slide-bg.jpg"
            fillMode: Image.PreserveAspectCrop
        }
        Column {
            anchors.left: parent.left
            anchors.leftMargin: 48
            anchors.verticalCenter: parent.verticalCenter
            width: parent.width * 0.62
            spacing: 14
            Text { text: heading; color: "white"; font.pixelSize: 30; font.weight: Font.DemiBold; wrapMode: Text.WordWrap; width: parent.width }
            Text { text: body; color: "#D8DAEA"; font.pixelSize: 16; wrapMode: Text.WordWrap; width: parent.width; lineHeight: 1.25 }
        }
    }

    VeyraSlide {
        heading: "Welcome to VeyraOS"
        body: "The Windows layout you know — Start menu, centered taskbar, File Explorer — on a fast, private Linux system."
    }
    VeyraSlide {
        heading: "Made for gaming"
        body: "Steam with Proton, Lutris, Gamescope, MangoHud and GameMode are ready. Press Meta+G for Gaming Mode."
    }
    VeyraSlide {
        heading: "NVIDIA, configured"
        body: "The proprietary NVIDIA driver is set up automatically for your GPU, with Wayland, Vulkan and hardware video decoding."
    }
    VeyraSlide {
        heading: "Apps in one click"
        body: "Open Software to install Discord, Spotify, Chrome, Office suites, VS Code and thousands more."
    }
    VeyraSlide {
        heading: "Safe updates"
        body: "With btrfs, a restore point can be created before every update, so you can always roll back."
    }

    function onActivate() { presentation.currentSlide = 0 }
    function onLeave() { }
}
