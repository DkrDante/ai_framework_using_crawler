# Crawler Prompt and Javascript Constants

CONSTRAINT_SYSTEM_PROMPT = (
    "You are an expert QA automation crawler assistant.\n"
    "Your job is to analyze a list of QA Test Cases and extract the precise, minimal set of URL paths and click targets that must be crawled to verify these test cases.\n\n"
    "Rules:\n"
    "- 'allowed_urls': a list of URL path strings (e.g. ['/home', '/login', '/products']). Do not include detail/preview templates (e.g. '/product/preview') unless a test case explicitly requires testing details/previews of individual items.\n"
    "- 'allowed_clicks': a list of specific button or link text labels that need to be clicked to trigger the transitions described in the test cases (e.g. ['Send Verification Code', 'Settings']).\n\n"
    "Respond ONLY with a JSON object containing keys 'allowed_urls' and 'allowed_clicks'. Do not include extra commentary."
)

EXTRACTION_JS = """
() => {
    function getLabelText(el) {
        if (el.id) {
            const label = document.querySelector(`label[for="${CSS.escape(el.id)}"]`);
            if (label && label.innerText.trim()) {
                return label.innerText.trim();
            }
        }
        let parent = el.parentElement;
        while (parent) {
            if (parent.tagName.toLowerCase() === 'label' && parent.innerText.trim()) {
                return parent.innerText.trim();
            }
            parent = parent.parentElement;
        }
        return '';
    }

    function getCssSelector(el) {
        if (el.id) {
            try {
                if (document.querySelectorAll(`#${CSS.escape(el.id)}`).length === 1) {
                    return `#${el.id}`;
                }
            } catch (e) {}
        }
        const path = [];
        let current = el;
        while (current && current.nodeType === Node.ELEMENT_NODE) {
            let selector = current.nodeName.toLowerCase();
            if (current.id) {
                selector += `#${current.id}`;
                path.unshift(selector);
                break;
            } else {
                let sib = current, sibIndex = 1;
                while (sib = sib.previousElementSibling) {
                    if (sib.nodeName.toLowerCase() === current.nodeName.toLowerCase()) {
                        sibIndex++;
                    }
                }
                if (sibIndex > 1 || current.nextElementSibling) {
                    selector += `:nth-of-type(${sibIndex})`;
                }
            }
            path.unshift(selector);
            current = current.parentElement;
        }
        return path.join(' > ');
    }

    function getPlaywrightLocator(el, tag, text, labelText) {
        const testId = el.getAttribute('data-testid');
        if (testId) {
            return `page.get_by_test_id("${testId}")`;
        }
        if (labelText) {
            const cleanLabel = labelText.replace(/\\n+/g, ' ').trim().substring(0, 50);
            return `page.get_by_label("${cleanLabel}")`;
        }
        const placeholder = el.getAttribute('placeholder');
        if (placeholder && (tag === 'input' || tag === 'textarea')) {
            const cleanPlaceholder = placeholder.replace(/\\n+/g, ' ').trim().substring(0, 50);
            return `page.get_by_placeholder("${cleanPlaceholder}")`;
        }
        let role = el.getAttribute('role');
        if (!role) {
            if (tag === 'button') role = 'button';
            else if (tag === 'a') role = 'link';
            else if (tag === 'input') {
                const type = el.getAttribute('type') || 'text';
                if (type === 'checkbox') role = 'checkbox';
                else if (type === 'radio') role = 'radio';
                else if (type === 'button' || type === 'submit' || type === 'reset') role = 'button';
                else role = 'textbox';
            }
            else if (tag === 'textarea') role = 'textbox';
            else if (tag === 'select') role = 'combobox';
        }
        const cleanText = text ? text.replace(/\\s+/g, ' ').trim().substring(0, 50) : '';
        if (role && cleanText) {
            return `page.get_by_role("${role}", { name: "${cleanText}" })`;
        } else if (role) {
            const nameAttr = el.getAttribute('name');
            if (nameAttr) {
                return `page.locator('${tag}[name="${nameAttr}"]')`;
            }
        }
        if (cleanText) {
            return `page.get_by_text("${cleanText}")`;
        }
        return `page.locator('${getCssSelector(el)}')`;
    }

    const interactiveSelector = 'a, button, input, textarea, select, [role="button"], [role="link"], [role="checkbox"], [role="radio"], [role="tab"], [role="menuitem"], [tabindex]:not([tabindex="-1"]), .cursor-pointer, [class*="cursor-pointer"]';

    function isVisible(el, rect) {
        const style = window.getComputedStyle(el);
        const isStyleVisible = style.display !== 'none' && style.visibility !== 'hidden' && style.opacity !== '0';
        const hasDimensions = rect.width > 0 && rect.height > 0;
        const isInViewport = rect.bottom >= 0 && rect.right >= 0 && 
                             rect.top <= window.innerHeight && rect.left <= window.innerWidth;
        return isStyleVisible && hasDimensions && isInViewport;
    }

    const list = [];
    const seen = new Set();
    let idCounter = 0;

    const interactiveCandidates = document.querySelectorAll(interactiveSelector);
    interactiveCandidates.forEach((el) => {
        const rect = el.getBoundingClientRect();
        if (isVisible(el, rect)) {
            seen.add(el);
            const tag = el.tagName.toLowerCase();
            const text = (el.innerText || el.value || el.getAttribute('aria-label') || '').trim();
            const labelText = getLabelText(el);
            list.push({
                id: idCounter++,
                kind: 'interactive',
                tag: tag,
                text: text.substring(0, 100),
                label: labelText,
                placeholder: el.getAttribute('placeholder') || '',
                type: el.getAttribute('type') || '',
                attributes: {
                    id: el.id || '',
                    name: el.getAttribute('name') || '',
                    class: el.getAttribute('class') || '',
                    href: el.getAttribute('href') || '',
                    role: el.getAttribute('role') || '',
                    'aria-haspopup': el.getAttribute('aria-haspopup') || ''
                },
                states: {
                    disabled: el.disabled || el.getAttribute('aria-disabled') === 'true',
                    readonly: el.readOnly || el.getAttribute('aria-readonly') === 'true',
                    checked: el.checked || el.getAttribute('aria-checked') === 'true',
                    required: el.required || el.getAttribute('aria-required') === 'true'
                },
                bounds: [
                    Math.round(rect.x),
                    Math.round(rect.y),
                    Math.round(rect.width),
                    Math.round(rect.height)
                ],
                selector: getCssSelector(el),
                playwright_locator: getPlaywrightLocator(el, tag, text, labelText)
            });
        }
    });

    const textTags = ['p', 'span', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'td', 'th', 'label', 'div'];
    const textCandidates = document.querySelectorAll(textTags.join(', '));
    textCandidates.forEach((el) => {
        if (seen.has(el)) return;
        if (el.matches(interactiveSelector)) return;
        const rect = el.getBoundingClientRect();
        if (isVisible(el, rect)) {
            let hasDirectText = false;
            for (let i = 0; i < el.childNodes.length; i++) {
                const child = el.childNodes[i];
                if (child.nodeType === 3 && child.nodeValue.trim()) {
                    hasDirectText = true;
                    break;
                }
            }
            if (hasDirectText) {
                seen.add(el);
                const tag = el.tagName.toLowerCase();
                const text = el.innerText.trim();
                const labelText = getLabelText(el);
                list.push({
                    id: idCounter++,
                    kind: 'text',
                    tag: tag,
                    text: text.substring(0, 100),
                    label: labelText,
                    placeholder: el.getAttribute('placeholder') || '',
                    type: el.getAttribute('type') || '',
                    attributes: {
                        id: el.id || '',
                        name: el.getAttribute('name') || '',
                        class: el.getAttribute('class') || '',
                        href: el.getAttribute('href') || '',
                        role: el.getAttribute('role') || ''
                    },
                    states: {
                        disabled: el.disabled || el.getAttribute('aria-disabled') === 'true',
                        readonly: el.readOnly || el.getAttribute('aria-readonly') === 'true',
                        checked: el.checked || el.getAttribute('aria-checked') === 'true',
                        required: el.required || el.getAttribute('aria-required') === 'true'
                    },
                    bounds: [
                        Math.round(rect.x),
                        Math.round(rect.y),
                        Math.round(rect.width),
                        Math.round(rect.height)
                    ],
                    selector: getCssSelector(el),
                    playwright_locator: getPlaywrightLocator(el, tag, text, labelText)
                });
            }
        }
    });
    return list;
}
"""
