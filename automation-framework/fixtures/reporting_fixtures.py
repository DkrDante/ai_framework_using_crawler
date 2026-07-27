import pytest
import allure
import os
import time
from playwright.sync_api import Page

@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    setattr(item, "rep_" + rep.when, rep)

    # Capture screenshots and videos for failed (call) or broken (setup) tests
    if rep.when in ("setup", "call") and rep.failed:
        # Attempt to get the page dynamically from standard or page-object fixtures
        page = None
        page_fixture_name = None
        for name in ("page", "unauthenticated_page", "module_page", "dashboard"):
            arg = item.funcargs.get(name)
            if not arg:
                continue
            if isinstance(arg, Page):
                page = arg
                page_fixture_name = name
                break
            elif hasattr(arg, "page") and isinstance(arg.page, Page):
                page = arg.page
                page_fixture_name = name
                break

        if page:
            try:
                # 1. Attach Screenshot immediately to capture visual state on failure
                screenshot = page.screenshot(full_page=True)
                allure.attach(
                    screenshot,
                    name=f"Screenshot_{item.name}",
                    attachment_type=allure.attachment_type.PNG
                )
                
                # 2. Attach Video if available
                if page.video:
                    # Determine if any of the page-related fixtures are broader than function scope.
                    # If it is a function-scoped context, we can safely close it now to force-flush video.
                    # If it is module-scoped (shared), do NOT close it to avoid breaking subsequent tests.
                    is_module_scoped = False
                    fixtures_to_check = []
                    if page_fixture_name:
                        fixtures_to_check.append(page_fixture_name)
                    for name in ("dashboard", "module_page"):
                        if name not in fixtures_to_check:
                            fixtures_to_check.append(name)
                            
                    for name in fixtures_to_check:
                        fixtureinfo = getattr(item, "_fixtureinfo", None)
                        if fixtureinfo and name in fixtureinfo.name2fixturedefs:
                            for fd in fixtureinfo.name2fixturedefs[name]:
                                if fd.scope in ("module", "class", "package", "session"):
                                    is_module_scoped = True
                                    break
                        if is_module_scoped:
                            break

                    if not is_module_scoped:
                        try:
                            page.context.close()
                        except Exception:
                            pass
                    
                    # Retry loop to ensure video file is completely written, exists, and is unlocked (crucial for Windows)
                    video_path = None
                    for _ in range(15):  # retry for up to 1.5 seconds
                        try:
                            video_path = page.video.path()
                            if video_path and os.path.exists(video_path) and os.path.getsize(video_path) > 0:
                                # Verify the file is readable and not locked
                                with open(video_path, "rb") as f:
                                    pass
                                break
                        except Exception:
                            pass
                        time.sleep(0.1)

                    if video_path and os.path.exists(video_path):
                        allure.attach.file(
                            video_path,
                            name=f"Video_{item.name}",
                            attachment_type=allure.attachment_type.WEBM
                        )
            except Exception as e:
                print(f"Failed to attach screenshot/video to Allure: {e}")
