@file:OptIn(ExperimentalMaterial3Api::class, ExperimentalAnimationApi::class)

package hoola.kit

// Made by Hoola App Sahayak. Navigation exactly as the approved design's STRUCTURE: bottom bar / floating pill /
// side bar (+ bottom bar) / rail / top tabs / none, the FAB kind (regular, extended, speed dial, menu, docked ...) and
// the screen transition. A plain back stack of screen ids: no string routes, no reflection.

import androidx.activity.compose.BackHandler
import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.ContentTransform
import androidx.compose.animation.ExperimentalAnimationApi
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.scaleIn
import androidx.compose.animation.scaleOut
import androidx.compose.animation.slideInHorizontally
import androidx.compose.animation.slideInVertically
import androidx.compose.animation.slideOutHorizontally
import androidx.compose.animation.slideOutVertically
import androidx.compose.animation.togetherWith
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawingPadding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.DrawerValue
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.ExtendedFloatingActionButton
import androidx.compose.material3.FloatingActionButton
import androidx.compose.material3.LargeFloatingActionButton
import androidx.compose.material3.ModalDrawerSheet
import androidx.compose.material3.ModalNavigationDrawer
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.NavigationBarItemDefaults
import androidx.compose.material3.NavigationDrawerItem
import androidx.compose.material3.NavigationRail
import androidx.compose.material3.NavigationRailItem
import androidx.compose.material3.SmallFloatingActionButton
import androidx.compose.material3.Text
import androidx.compose.material3.rememberDrawerState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.runtime.staticCompositionLocalOf
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.key
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.launch

data class TabSpec(val id: String, val label: String, val icon: String)
data class FabAction(val label: String, val icon: String, val go: String)

class Nav(val start: String, val tabs: List<TabSpec>, val screens: Set<String>) {
    val stack = mutableStateListOf(start)
    var forward by mutableStateOf(true)
    val current: String get() = stack.last()
    val canBack: Boolean get() = stack.size > 1
    var hasDrawer: Boolean = false
    /** Set by Page: true while the screen has its own sticky bottom action. */
    var fabHidden by mutableStateOf(false)
    internal var drawerOpener: (() -> Unit)? = null

    /** Open a screen (a tab switches tabs). Unknown ids are ignored so a stray link can't crash the app. */
    fun go(id: String) {
        if (id !in screens || id == current) return
        forward = true
        if (tabs.any { it.id == id }) { stack.clear(); stack.add(id) } else stack.add(id)
    }

    /** Open a record's screen: remembers which record (AppState.selected[list]). */
    fun open(id: String, list: String, recordId: String) { AppState.select(list, recordId); go(id) }

    fun back(): Boolean {
        if (stack.size <= 1) return false
        forward = false
        stack.removeAt(stack.lastIndex)
        return true
    }

    fun home() { forward = false; stack.clear(); stack.add(start) }
    fun openDrawer() { drawerOpener?.invoke() }
    val onTab: Boolean get() = tabs.any { it.id == current }
}

/** Outside the shell (first-run splash / consent) a quiet Nav that goes nowhere: no crash. */
val LocalNav = staticCompositionLocalOf<Nav> { Nav("_", emptyList(), emptySet()) }

@Composable
fun AppShell(nav: Nav, fabMain: FabAction?, fabActions: List<FabAction>, title: String, screen: @Composable (String) -> Unit) {
    val look = H.look
    val c = H.c
    val drawerState = rememberDrawerState(DrawerValue.Closed)
    val scope = rememberCoroutineScope()
    val drawer = look.nav in setOf("drawer", "drawer_bar", "side_sheet")
    nav.hasDrawer = drawer
    nav.drawerOpener = { scope.launch { drawerState.open() } }
    BackHandler(enabled = nav.canBack) { nav.back() }

    val body: @Composable () -> Unit = {
        CompositionLocalProvider(LocalNav provides nav) {
            Box(Modifier.fillMaxSize().background(c.bg).safeDrawingPadding()) {
                Row(Modifier.fillMaxSize()) {
                    if (look.nav == "rail" && nav.onTab) Rail(nav)
                    Column(Modifier.weight(1f).fillMaxSize()) {
                        if (look.nav in setOf("top_tabs", "segmented_top") && nav.onTab) TopTabs(nav)
                        Box(Modifier.weight(1f).fillMaxWidth()) { Screens(nav, screen) }
                        if (look.nav in setOf("bar", "bar_labels", "bar_minimal", "bottom_app_bar", "drawer_bar") && nav.onTab) BottomBar(nav)
                    }
                }
                if (look.nav == "floating_pill" && nav.onTab) FloatingPill(nav, Modifier.align(Alignment.BottomCenter))
                if (look.fab != "none" && fabMain != null && nav.onTab && !nav.fabHidden) Fab(look.fab, fabMain, fabActions, nav,
                    Modifier.align(if (look.fab == "docked") Alignment.BottomCenter else Alignment.BottomEnd)
                        .padding(end = if (look.fab == "docked") 0.dp else 16.dp, bottom = if (look.nav == "none" || look.nav == "rail") 20.dp else 92.dp))
            }
        }
    }
    if (drawer) {
        ModalNavigationDrawer(drawerState = drawerState, drawerContent = {
            ModalDrawerSheet(drawerContainerColor = c.surface) {
                Text(title, style = H.t.h2, modifier = Modifier.padding(20.dp))
                nav.tabs.forEach { t ->
                    NavigationDrawerItem(
                        label = { Text(t.label, style = H.t.title) }, selected = nav.current == t.id,
                        icon = { HIcon(t.icon) },
                        onClick = { nav.go(t.id); scope.launch { drawerState.close() } },
                        modifier = Modifier.padding(horizontal = 12.dp),
                    )
                }
            }
        }, content = body)
    } else body()
}

@Composable
private fun Screens(nav: Nav, screen: @Composable (String) -> Unit) {
    val t = H.look.transition
    val version = AppData.version.value
    AnimatedContent(targetState = nav.current, transitionSpec = { spec(t, nav.forward) }, label = "screen") { id ->
        key(id, version) { screen(id) }
    }
}

private fun spec(t: String, fwd: Boolean): ContentTransform = when (t) {
    "push", "axis_x", "cube", "flip", "curl" ->
        (slideInHorizontally { w -> if (fwd) w / 3 else -w / 3 } + fadeIn()) togetherWith (slideOutHorizontally { w -> if (fwd) -w / 4 else w / 4 } + fadeOut())
    "axis_y", "sheet", "reveal" ->
        (slideInVertically { h -> if (fwd) h / 5 else -h / 5 } + fadeIn()) togetherWith fadeOut()
    "zoom", "axis_z", "container" -> (scaleIn(initialScale = 0.94f) + fadeIn()) togetherWith (scaleOut(targetScale = 1.04f) + fadeOut())
    else -> fadeIn() togetherWith fadeOut()
}

@Composable
private fun BottomBar(nav: Nav) {
    val c = H.c
    val labels = H.look.nav != "bar_minimal"
    NavigationBar(containerColor = c.surface) {
        nav.tabs.forEach { t ->
            NavigationBarItem(
                selected = nav.current == t.id, onClick = { nav.go(t.id) },
                icon = { HIcon(t.icon, tint = if (nav.current == t.id) c.primaryText else c.muted) },
                label = { Text(t.label, maxLines = 1) },
                alwaysShowLabel = labels,
                colors = NavigationBarItemDefaults.colors(indicatorColor = c.tint, selectedTextColor = c.primaryText, unselectedTextColor = c.muted),
            )
        }
    }
}

@Composable
private fun FloatingPill(nav: Nav, modifier: Modifier) {
    val c = H.c
    Row(
        modifier.navigationBarsPadding().padding(bottom = 16.dp, start = 24.dp, end = 24.dp).shadow(10.dp, RoundedCornerShape(50))
            .background(c.surface, RoundedCornerShape(50)).padding(horizontal = 10.dp, vertical = 6.dp),
        horizontalArrangement = Arrangement.spacedBy(4.dp), verticalAlignment = Alignment.CenterVertically,
    ) {
        nav.tabs.forEach { t ->
            val on = nav.current == t.id
            Box(
                Modifier.size(52.dp).background(if (on) c.primary else c.surface, CircleShape).clickable { nav.go(t.id) },
                contentAlignment = Alignment.Center,
            ) { HIcon(t.icon, tint = if (on) c.onPrimary else c.muted, description = t.label) }
        }
    }
}

@Composable
private fun Rail(nav: Nav) {
    val c = H.c
    NavigationRail(containerColor = c.surface) {
        nav.tabs.forEach { t ->
            NavigationRailItem(selected = nav.current == t.id, onClick = { nav.go(t.id) }, icon = { HIcon(t.icon) }, label = { Text(t.label, maxLines = 1) })
        }
    }
}

@Composable
private fun TopTabs(nav: Nav) {
    Row(Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()).padding(horizontal = 12.dp, vertical = 8.dp), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        nav.tabs.forEach { t -> Chip(t.label, selected = nav.current == t.id, icon = t.icon) { nav.go(t.id) } }
    }
}

@Composable
private fun Fab(kind: String, main: FabAction, actions: List<FabAction>, nav: Nav, modifier: Modifier) {
    val c = H.c
    var open by remember { mutableStateOf(false) }
    Column(modifier, horizontalAlignment = Alignment.End, verticalArrangement = Arrangement.spacedBy(10.dp)) {
        if (open && kind in setOf("speed_dial", "menu")) {
            actions.forEach { a ->
                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text(a.label, style = H.t.title, modifier = Modifier.background(c.surface, RoundedCornerShape(8.dp)).padding(horizontal = 10.dp, vertical = 6.dp))
                    SmallFloatingActionButton(onClick = { open = false; nav.go(a.go) }, containerColor = c.tint) { HIcon(a.icon, tint = c.primaryText, description = a.label) }
                }
            }
        }
        val click: () -> Unit = {
            if (kind in setOf("speed_dial", "menu") && actions.isNotEmpty()) open = !open else nav.go(main.go)
            Unit
        }
        when (kind) {
            "extended" -> ExtendedFloatingActionButton(text = { Text(main.label) }, icon = { HIcon(main.icon, tint = c.onPrimary) }, onClick = click,
                containerColor = c.primary, contentColor = c.onPrimary)
            "small" -> SmallFloatingActionButton(onClick = click, containerColor = c.primary) { HIcon(main.icon, tint = c.onPrimary, description = main.label) }
            "large" -> LargeFloatingActionButton(onClick = click, containerColor = c.primary) { HIcon(main.icon, size = 30.dp, tint = c.onPrimary, description = main.label) }
            else -> FloatingActionButton(onClick = click, containerColor = c.primary) { HIcon(if (open) "x" else main.icon, tint = c.onPrimary, description = main.label) }
        }
    }
}
