import QtQuick 2.0
import Sailfish.Silica 1.0

ComboBox{
    id : cBox

    // selected item, only assigned if user
    // clicks on an item in the context menu,
    // not if changing the current item index
    property variant item

    ContextMenu {
        id : cMenu
        Repeater {
            id : cRepeater
            MenuItem {
                text : modelData.text
                onClicked : {
                    cBox.currentItem : modelData
                }
            }
        }
    }
    property alias model : cBox.cMenu.cRepeater.model
    // how does this work ?
    //
    // Menu items are added with a ListModel to the
    // model property, which dynamically adds them to the
    // context menu. Once an item is clicked, its underlying
    // ListElement is returned so onCurrentItemChanged
    // is triggered.

    onCurrentIndexChanged: {
            // assign selected item to the item
            // property, so that the onItemChanged
            // signal is triggered
            cBox.item = cBox.model.get(currentIndex)
        }
    }
}