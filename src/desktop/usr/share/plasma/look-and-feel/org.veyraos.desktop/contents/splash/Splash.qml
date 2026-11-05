/*
 * VeyraOS login splash (KSplash QML). Shown while Plasma starts.
 * Plain QtQuick only, so it works with any Plasma 6 release.
 */
import QtQuick

Rectangle {
    id: root
    color: "#05060F"

    property int stage

    onStageChanged: {
        if (stage == 2) introAnimation.running = true
    }

    Item {
        id: content
        anchors.fill: parent
        opacity: 0

        Image {
            id: logo
            anchors.centerIn: parent
            anchors.verticalCenterOffset: -40
            source: "images/logo.svgz"
            sourceSize.width: 128
            sourceSize.height: 128
            fillMode: Image.PreserveAspectFit
        }

        Item {
            id: busy
            width: 48; height: 48
            anchors.top: logo.bottom
            anchors.topMargin: 56
            anchors.horizontalCenter: parent.horizontalCenter

            // Six dots orbiting with easing, in the VeyraOS accent colours
            Repeater {
                model: 6
                delegate: Rectangle {
                    id: dot
                    required property int index
                    width: 7; height: 7; radius: 3.5
                    color: index % 2 ? "#34D3EE" : "#A78BFA"
                    property real angle: 0
                    x: busy.width / 2 + 20 * Math.cos(angle) - width / 2
                    y: busy.height / 2 + 20 * Math.sin(angle) - height / 2
                    SequentialAnimation on angle {
                        loops: Animation.Infinite
                        PauseAnimation { duration: dot.index * 110 }
                        NumberAnimation { from: Math.PI / 2; to: Math.PI / 2 + 2 * Math.PI; duration: 1500; easing.type: Easing.InOutCubic }
                        PauseAnimation { duration: (5 - dot.index) * 110 }
                    }
                }
            }
        }
    }

    OpacityAnimator {
        id: introAnimation
        running: false
        target: content
        from: 0
        to: 1
        duration: 400
        easing.type: Easing.InOutQuad
    }
}
