import Toybox.Application;
import Toybox.Lang;
import Toybox.WatchUi;

class GaugeFaceApp extends Application.AppBase {

    private var _view as GaugeFaceView?;

    function initialize() {
        AppBase.initialize();
    }

    function onStart(state as Dictionary?) as Void {
    }

    function onStop(state as Dictionary?) as Void {
    }

    function getInitialView() as [WatchUi.Views] or [WatchUi.Views, WatchUi.InputDelegates] {
        _view = new GaugeFaceView();
        return [_view];
    }

    function onSettingsChanged() as Void {
        if (_view != null) {
            _view.onSettingsChanged();
        }
        WatchUi.requestUpdate();
    }
}
