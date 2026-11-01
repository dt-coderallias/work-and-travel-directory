// Streamlit only sends a text box's value on Enter, or Ctrl+Enter in a text
// area, or when it loses focus. This presses that key once the visitor pauses,
// so results follow their typing. If a Streamlit upgrade breaks it, the boxes
// still work the normal way.
if (!window.liveTypingReady) {
  window.liveTypingReady = true;
  const WATCHED = '.st-key-f_query, [class*="_details"]';
  let timer;

  const pressEnter = (box) => {
    const ctrlKey = box.tagName === "TEXTAREA";
    for (const type of ["keydown", "keypress", "keyup"]) {
      box.dispatchEvent(new KeyboardEvent(type, {
        key: "Enter", code: "Enter", keyCode: 13, which: 13, charCode: 13,
        ctrlKey, bubbles: true, cancelable: true,
      }));
    }
  };

  document.addEventListener("input", (event) => {
    const box = event.target;
    if (!box.closest || !box.closest(WATCHED)) return;
    clearTimeout(timer);
    timer = setTimeout(() => pressEnter(box), 300);
  }, true);
}
