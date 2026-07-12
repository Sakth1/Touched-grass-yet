import flet as ft

from src.UI.home_page import HomePage

class MainView:
    def __init__(self, page: ft.Page):
        super().__init__()
        self.page = page
        self.home_page = HomePage(page)
        self.page.width = 400
        self.page.height = 400
        self.page.drawer = ft.NavigationDrawer(           
            on_change=self.on_navigation_drawer_change,
            controls=[
            ft.Container(height=12),
            ft.NavigationDrawerDestination(
                label="Home",
                icon=ft.Icons.HOME,
            ),
            ]
        )

        self.page.add(
            ft.SafeArea(
                content=ft.Button(
                    "Show drawer",
                    icon=ft.Icons.MENU,
                    on_click=self.handle_show_drawer,
                ),
            )
        )


    async def handle_show_drawer(self, e: ft.Event[ft.Button]):
        print("Show drawer")
        await self.page.show_drawer()


    def on_navigation_drawer_change(self, e):
        print(e)

def entrypoint(page: ft.Page):
    MainView(page)
