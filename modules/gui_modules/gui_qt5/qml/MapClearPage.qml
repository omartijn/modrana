import QtQuick 2.0
import UC 1.0
import "modrana_components"

IconGridPage {
    id : mapMenuPage

    function setLayer(layerId) {
        rWin.mapPage.getMap().setLayerById(0, layerId)
        rWin.push(null, !rWin.animate)
    }

    function getPage(menu){
        // we kinda miss-use this function there as we always go back to the map
        if (menu == "all") {
            rWin.mapPage.clearSearchMarkers()
            rWin.mapPage.clearPOIMarkers()
            rWin.mapPage.clearTracklogs()
        } else if (menu == "search") {
            rWin.mapPage.clearSearchMarkers()
        } else if (menu == "POI") {
            rWin.mapPage.clearPOIMarkers()
        } else if (menu == "tracklogs") {
            rWin.mapPage.clearTracklogs()
        }
        rWin.push(null, !rWin.animate)
    }

    model : ListModel {
        id : testModel
        ListElement {
            caption : QT_TRANSLATE_NOOP("IconGridPage", "All")
            icon : "debug.png"
            menu : "all"
        }
        ListElement {
            caption : QT_TRANSLATE_NOOP("IconGridPage", "Search")
            icon : "search.png"
            menu : "search"
        }
        ListElement {
            caption : QT_TRANSLATE_NOOP("IconGridPage", "POI")
            icon : "poi.png"
            menu : "POI"
        }
        ListElement {
            caption : QT_TRANSLATE_NOOP("IconGridPage", "Tracklogs")
            icon : "tracklogs.png"
            menu : "tracklogs"
        }
    }
}