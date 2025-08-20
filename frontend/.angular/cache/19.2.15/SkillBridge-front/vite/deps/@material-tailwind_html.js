import "./chunk-TXDUYLVM.js";

// node_modules/@material-tailwind/html/dist/material-tailwind.esm.js
var popperLoaded = false;
var popperReady = null;
function loadPopperJs() {
  if (popperLoaded) {
    return popperReady;
  }
  popperLoaded = true;
  popperReady = new Promise((resolve, reject) => {
    if (window.Popper) {
      resolve(window.Popper);
      return;
    }
    const script = document.createElement("script");
    script.src = "https://unpkg.com/@popperjs/core@2";
    script.defer = true;
    script.onload = () => {
      resolve(window.Popper);
    };
    script.onerror = () => {
      reject(new Error("Failed to load Popper.js"));
    };
    document.head.appendChild(script);
  });
  return popperReady;
}
var initializedElements$2 = /* @__PURE__ */ new WeakSet();
function closeAlert(event) {
  const button = event.currentTarget;
  const alert = button.closest('[role="alert"]');
  if (alert) {
    alert.remove();
  }
}
function initAlert() {
  document.querySelectorAll("[data-dismiss='alert']").forEach((button) => {
    if (!initializedElements$2.has(button)) {
      button.addEventListener("click", closeAlert);
      initializedElements$2.add(button);
    }
  });
}
if (typeof window !== "undefined") {
  document.addEventListener("DOMContentLoaded", () => {
    initAlert();
    const observer = new MutationObserver(() => {
      initAlert();
    });
    observer.observe(document.body, {
      childList: true,
      subtree: true
    });
  });
}
var initializedElements$1 = /* @__PURE__ */ new WeakSet();
function changeMainImage(event) {
  const thumbnail = event.currentTarget;
  const mainImage = document.querySelector("[data-main-image]");
  if (mainImage) {
    mainImage.src = thumbnail.src;
    document.querySelectorAll("[data-thumbnail]").forEach((thumb) => {
      thumb.classList.remove("active-thumbnail");
    });
    thumbnail.classList.add("active-thumbnail");
  }
}
function initGallery() {
  document.querySelectorAll("[data-thumbnail]").forEach((thumbnail) => {
    if (!initializedElements$1.has(thumbnail)) {
      thumbnail.addEventListener("click", changeMainImage);
      initializedElements$1.add(thumbnail);
    }
  });
}
function cleanupGallery() {
  document.querySelectorAll("[data-thumbnail]").forEach((thumbnail) => {
    if (initializedElements$1.has(thumbnail)) {
      thumbnail.removeEventListener("click", changeMainImage);
      initializedElements$1.delete(thumbnail);
    }
  });
}
if (typeof window !== "undefined") {
  document.addEventListener("DOMContentLoaded", () => {
    initGallery();
    const observer = new MutationObserver(() => {
      initGallery();
    });
    observer.observe(document.body, {
      childList: true,
      subtree: true
    });
  });
}
var initializedElements = /* @__PURE__ */ new WeakSet();
function toggleCollapse(event) {
  const button = event.currentTarget;
  if (!button) return;
  const collapseID = button.getAttribute("data-target");
  if (collapseID && collapseID.startsWith("#")) {
    const collapseElement = document.querySelector(collapseID);
    const isExpanded = button.getAttribute("aria-expanded") === "true";
    if (collapseElement) {
      collapseElement.style.maxHeight = isExpanded ? "0" : `${collapseElement.scrollHeight}px`;
      button.setAttribute("aria-expanded", `${!isExpanded}`);
      const icon = button.querySelector("[data-icon]");
      if (icon) {
        icon.classList.toggle("rotate-180", !isExpanded);
      }
    }
  }
}
function initCollapse() {
  document.querySelectorAll("[data-toggle='collapse']").forEach((button) => {
    if (!initializedElements.has(button)) {
      button.addEventListener("click", toggleCollapse);
      initializedElements.add(button);
    }
  });
}
if (typeof window !== "undefined") {
  document.addEventListener("DOMContentLoaded", () => {
    initCollapse();
    const observer = new MutationObserver(() => {
      initCollapse();
    });
    observer.observe(document.body, {
      childList: true,
      subtree: true
    });
  });
}
var Collapse = class {
  /**
   * Creates an instance of Collapse.
   * @param button - The button element or its selector controlling the collapsible content.
   * @param collapseElement - The collapsible content element or its selector.
   * @param config - Configuration options for the collapse.
   */
  constructor(button, collapseElement, config = {}) {
    this.button = this.resolveElement(button, "Button element not found");
    this.collapseElement = this.resolveElement(collapseElement, "Collapsible content element not found");
    this.config = config;
    this.init();
  }
  /**
   * Resolves an element from an HTMLElement or selector string.
   * @param elementOrSelector - HTMLElement or a selector string.
   * @param errorMessage - Error message if the element is not found.
   * @returns The resolved HTMLElement.
   */
  resolveElement(elementOrSelector, errorMessage) {
    if (typeof elementOrSelector === "string") {
      const resolvedElement = document.querySelector(elementOrSelector);
      if (!resolvedElement) throw new Error(errorMessage);
      return resolvedElement;
    } else if (elementOrSelector instanceof HTMLElement) {
      return elementOrSelector;
    }
    throw new Error(errorMessage);
  }
  /**
   * Initializes the Collapse component by attaching event listeners.
   */
  init() {
    this.button.addEventListener("click", () => this.toggle());
  }
  /**
   * Toggles the collapsible content visibility.
   */
  toggle() {
    const isExpanded = this.button.getAttribute("aria-expanded") === "true";
    this.collapseElement.style.maxHeight = isExpanded ? "0" : `${this.collapseElement.scrollHeight}px`;
    this.button.setAttribute("aria-expanded", `${!isExpanded}`);
    if (this.config.iconSelector) {
      const icon = document.querySelector(this.config.iconSelector);
      if (icon) {
        icon.classList.toggle("rotate-180", !isExpanded);
      }
    }
  }
  /**
   * Expands the collapsible content.
   */
  expand() {
    this.collapseElement.style.maxHeight = `${this.collapseElement.scrollHeight}px`;
    this.button.setAttribute("aria-expanded", "true");
    if (this.config.iconSelector) {
      const icon = document.querySelector(this.config.iconSelector);
      if (icon) {
        icon.classList.add("rotate-180");
      }
    }
  }
  /**
   * Collapses the collapsible content.
   */
  collapse() {
    this.collapseElement.style.maxHeight = "0";
    this.button.setAttribute("aria-expanded", "false");
    if (this.config.iconSelector) {
      const icon = document.querySelector(this.config.iconSelector);
      if (icon) {
        icon.classList.remove("rotate-180");
      }
    }
  }
};
function __awaiter(thisArg, _arguments, P, generator) {
  function adopt(value) {
    return value instanceof P ? value : new P(function(resolve) {
      resolve(value);
    });
  }
  return new (P || (P = Promise))(function(resolve, reject) {
    function fulfilled(value) {
      try {
        step(generator.next(value));
      } catch (e) {
        reject(e);
      }
    }
    function rejected(value) {
      try {
        step(generator["throw"](value));
      } catch (e) {
        reject(e);
      }
    }
    function step(result) {
      result.done ? resolve(result.value) : adopt(result.value).then(fulfilled, rejected);
    }
    step((generator = generator.apply(thisArg, _arguments || [])).next());
  });
}
var top = "top";
var bottom = "bottom";
var right = "right";
var left = "left";
var auto = "auto";
var basePlacements = [top, bottom, right, left];
var start = "start";
var end = "end";
var clippingParents = "clippingParents";
var viewport = "viewport";
var popper = "popper";
var reference = "reference";
var variationPlacements = basePlacements.reduce(function(acc, placement) {
  return acc.concat([placement + "-" + start, placement + "-" + end]);
}, []);
var placements = [].concat(basePlacements, [auto]).reduce(function(acc, placement) {
  return acc.concat([placement, placement + "-" + start, placement + "-" + end]);
}, []);
var beforeRead = "beforeRead";
var read = "read";
var afterRead = "afterRead";
var beforeMain = "beforeMain";
var main = "main";
var afterMain = "afterMain";
var beforeWrite = "beforeWrite";
var write = "write";
var afterWrite = "afterWrite";
var modifierPhases = [beforeRead, read, afterRead, beforeMain, main, afterMain, beforeWrite, write, afterWrite];
function getNodeName(element) {
  return element ? (element.nodeName || "").toLowerCase() : null;
}
function getWindow(node) {
  if (node == null) {
    return window;
  }
  if (node.toString() !== "[object Window]") {
    var ownerDocument = node.ownerDocument;
    return ownerDocument ? ownerDocument.defaultView || window : window;
  }
  return node;
}
function isElement(node) {
  var OwnElement = getWindow(node).Element;
  return node instanceof OwnElement || node instanceof Element;
}
function isHTMLElement(node) {
  var OwnElement = getWindow(node).HTMLElement;
  return node instanceof OwnElement || node instanceof HTMLElement;
}
function isShadowRoot(node) {
  if (typeof ShadowRoot === "undefined") {
    return false;
  }
  var OwnElement = getWindow(node).ShadowRoot;
  return node instanceof OwnElement || node instanceof ShadowRoot;
}
function applyStyles(_ref) {
  var state = _ref.state;
  Object.keys(state.elements).forEach(function(name) {
    var style = state.styles[name] || {};
    var attributes = state.attributes[name] || {};
    var element = state.elements[name];
    if (!isHTMLElement(element) || !getNodeName(element)) {
      return;
    }
    Object.assign(element.style, style);
    Object.keys(attributes).forEach(function(name2) {
      var value = attributes[name2];
      if (value === false) {
        element.removeAttribute(name2);
      } else {
        element.setAttribute(name2, value === true ? "" : value);
      }
    });
  });
}
function effect$2(_ref2) {
  var state = _ref2.state;
  var initialStyles = {
    popper: {
      position: state.options.strategy,
      left: "0",
      top: "0",
      margin: "0"
    },
    arrow: {
      position: "absolute"
    },
    reference: {}
  };
  Object.assign(state.elements.popper.style, initialStyles.popper);
  state.styles = initialStyles;
  if (state.elements.arrow) {
    Object.assign(state.elements.arrow.style, initialStyles.arrow);
  }
  return function() {
    Object.keys(state.elements).forEach(function(name) {
      var element = state.elements[name];
      var attributes = state.attributes[name] || {};
      var styleProperties = Object.keys(state.styles.hasOwnProperty(name) ? state.styles[name] : initialStyles[name]);
      var style = styleProperties.reduce(function(style2, property) {
        style2[property] = "";
        return style2;
      }, {});
      if (!isHTMLElement(element) || !getNodeName(element)) {
        return;
      }
      Object.assign(element.style, style);
      Object.keys(attributes).forEach(function(attribute) {
        element.removeAttribute(attribute);
      });
    });
  };
}
var applyStyles$1 = {
  name: "applyStyles",
  enabled: true,
  phase: "write",
  fn: applyStyles,
  effect: effect$2,
  requires: ["computeStyles"]
};
function getBasePlacement(placement) {
  return placement.split("-")[0];
}
var max = Math.max;
var min = Math.min;
var round = Math.round;
function getUAString() {
  var uaData = navigator.userAgentData;
  if (uaData != null && uaData.brands && Array.isArray(uaData.brands)) {
    return uaData.brands.map(function(item) {
      return item.brand + "/" + item.version;
    }).join(" ");
  }
  return navigator.userAgent;
}
function isLayoutViewport() {
  return !/^((?!chrome|android).)*safari/i.test(getUAString());
}
function getBoundingClientRect(element, includeScale, isFixedStrategy) {
  if (includeScale === void 0) {
    includeScale = false;
  }
  if (isFixedStrategy === void 0) {
    isFixedStrategy = false;
  }
  var clientRect = element.getBoundingClientRect();
  var scaleX = 1;
  var scaleY = 1;
  if (includeScale && isHTMLElement(element)) {
    scaleX = element.offsetWidth > 0 ? round(clientRect.width) / element.offsetWidth || 1 : 1;
    scaleY = element.offsetHeight > 0 ? round(clientRect.height) / element.offsetHeight || 1 : 1;
  }
  var _ref = isElement(element) ? getWindow(element) : window, visualViewport = _ref.visualViewport;
  var addVisualOffsets = !isLayoutViewport() && isFixedStrategy;
  var x = (clientRect.left + (addVisualOffsets && visualViewport ? visualViewport.offsetLeft : 0)) / scaleX;
  var y = (clientRect.top + (addVisualOffsets && visualViewport ? visualViewport.offsetTop : 0)) / scaleY;
  var width = clientRect.width / scaleX;
  var height = clientRect.height / scaleY;
  return {
    width,
    height,
    top: y,
    right: x + width,
    bottom: y + height,
    left: x,
    x,
    y
  };
}
function getLayoutRect(element) {
  var clientRect = getBoundingClientRect(element);
  var width = element.offsetWidth;
  var height = element.offsetHeight;
  if (Math.abs(clientRect.width - width) <= 1) {
    width = clientRect.width;
  }
  if (Math.abs(clientRect.height - height) <= 1) {
    height = clientRect.height;
  }
  return {
    x: element.offsetLeft,
    y: element.offsetTop,
    width,
    height
  };
}
function contains(parent, child) {
  var rootNode = child.getRootNode && child.getRootNode();
  if (parent.contains(child)) {
    return true;
  } else if (rootNode && isShadowRoot(rootNode)) {
    var next = child;
    do {
      if (next && parent.isSameNode(next)) {
        return true;
      }
      next = next.parentNode || next.host;
    } while (next);
  }
  return false;
}
function getComputedStyle(element) {
  return getWindow(element).getComputedStyle(element);
}
function isTableElement(element) {
  return ["table", "td", "th"].indexOf(getNodeName(element)) >= 0;
}
function getDocumentElement(element) {
  return ((isElement(element) ? element.ownerDocument : (
    // $FlowFixMe[prop-missing]
    element.document
  )) || window.document).documentElement;
}
function getParentNode(element) {
  if (getNodeName(element) === "html") {
    return element;
  }
  return (
    // this is a quicker (but less type safe) way to save quite some bytes from the bundle
    // $FlowFixMe[incompatible-return]
    // $FlowFixMe[prop-missing]
    element.assignedSlot || // step into the shadow DOM of the parent of a slotted node
    element.parentNode || // DOM Element detected
    (isShadowRoot(element) ? element.host : null) || // ShadowRoot detected
    // $FlowFixMe[incompatible-call]: HTMLElement is a Node
    getDocumentElement(element)
  );
}
function getTrueOffsetParent(element) {
  if (!isHTMLElement(element) || // https://github.com/popperjs/popper-core/issues/837
  getComputedStyle(element).position === "fixed") {
    return null;
  }
  return element.offsetParent;
}
function getContainingBlock(element) {
  var isFirefox = /firefox/i.test(getUAString());
  var isIE = /Trident/i.test(getUAString());
  if (isIE && isHTMLElement(element)) {
    var elementCss = getComputedStyle(element);
    if (elementCss.position === "fixed") {
      return null;
    }
  }
  var currentNode = getParentNode(element);
  if (isShadowRoot(currentNode)) {
    currentNode = currentNode.host;
  }
  while (isHTMLElement(currentNode) && ["html", "body"].indexOf(getNodeName(currentNode)) < 0) {
    var css = getComputedStyle(currentNode);
    if (css.transform !== "none" || css.perspective !== "none" || css.contain === "paint" || ["transform", "perspective"].indexOf(css.willChange) !== -1 || isFirefox && css.willChange === "filter" || isFirefox && css.filter && css.filter !== "none") {
      return currentNode;
    } else {
      currentNode = currentNode.parentNode;
    }
  }
  return null;
}
function getOffsetParent(element) {
  var window2 = getWindow(element);
  var offsetParent = getTrueOffsetParent(element);
  while (offsetParent && isTableElement(offsetParent) && getComputedStyle(offsetParent).position === "static") {
    offsetParent = getTrueOffsetParent(offsetParent);
  }
  if (offsetParent && (getNodeName(offsetParent) === "html" || getNodeName(offsetParent) === "body" && getComputedStyle(offsetParent).position === "static")) {
    return window2;
  }
  return offsetParent || getContainingBlock(element) || window2;
}
function getMainAxisFromPlacement(placement) {
  return ["top", "bottom"].indexOf(placement) >= 0 ? "x" : "y";
}
function within(min$1, value, max$1) {
  return max(min$1, min(value, max$1));
}
function withinMaxClamp(min2, value, max2) {
  var v = within(min2, value, max2);
  return v > max2 ? max2 : v;
}
function getFreshSideObject() {
  return {
    top: 0,
    right: 0,
    bottom: 0,
    left: 0
  };
}
function mergePaddingObject(paddingObject) {
  return Object.assign({}, getFreshSideObject(), paddingObject);
}
function expandToHashMap(value, keys) {
  return keys.reduce(function(hashMap, key) {
    hashMap[key] = value;
    return hashMap;
  }, {});
}
var toPaddingObject = function toPaddingObject2(padding, state) {
  padding = typeof padding === "function" ? padding(Object.assign({}, state.rects, {
    placement: state.placement
  })) : padding;
  return mergePaddingObject(typeof padding !== "number" ? padding : expandToHashMap(padding, basePlacements));
};
function arrow(_ref) {
  var _state$modifiersData$;
  var state = _ref.state, name = _ref.name, options = _ref.options;
  var arrowElement = state.elements.arrow;
  var popperOffsets2 = state.modifiersData.popperOffsets;
  var basePlacement = getBasePlacement(state.placement);
  var axis = getMainAxisFromPlacement(basePlacement);
  var isVertical = [left, right].indexOf(basePlacement) >= 0;
  var len = isVertical ? "height" : "width";
  if (!arrowElement || !popperOffsets2) {
    return;
  }
  var paddingObject = toPaddingObject(options.padding, state);
  var arrowRect = getLayoutRect(arrowElement);
  var minProp = axis === "y" ? top : left;
  var maxProp = axis === "y" ? bottom : right;
  var endDiff = state.rects.reference[len] + state.rects.reference[axis] - popperOffsets2[axis] - state.rects.popper[len];
  var startDiff = popperOffsets2[axis] - state.rects.reference[axis];
  var arrowOffsetParent = getOffsetParent(arrowElement);
  var clientSize = arrowOffsetParent ? axis === "y" ? arrowOffsetParent.clientHeight || 0 : arrowOffsetParent.clientWidth || 0 : 0;
  var centerToReference = endDiff / 2 - startDiff / 2;
  var min2 = paddingObject[minProp];
  var max2 = clientSize - arrowRect[len] - paddingObject[maxProp];
  var center = clientSize / 2 - arrowRect[len] / 2 + centerToReference;
  var offset2 = within(min2, center, max2);
  var axisProp = axis;
  state.modifiersData[name] = (_state$modifiersData$ = {}, _state$modifiersData$[axisProp] = offset2, _state$modifiersData$.centerOffset = offset2 - center, _state$modifiersData$);
}
function effect$1(_ref2) {
  var state = _ref2.state, options = _ref2.options;
  var _options$element = options.element, arrowElement = _options$element === void 0 ? "[data-popper-arrow]" : _options$element;
  if (arrowElement == null) {
    return;
  }
  if (typeof arrowElement === "string") {
    arrowElement = state.elements.popper.querySelector(arrowElement);
    if (!arrowElement) {
      return;
    }
  }
  if (!contains(state.elements.popper, arrowElement)) {
    return;
  }
  state.elements.arrow = arrowElement;
}
var arrow$1 = {
  name: "arrow",
  enabled: true,
  phase: "main",
  fn: arrow,
  effect: effect$1,
  requires: ["popperOffsets"],
  requiresIfExists: ["preventOverflow"]
};
function getVariation(placement) {
  return placement.split("-")[1];
}
var unsetSides = {
  top: "auto",
  right: "auto",
  bottom: "auto",
  left: "auto"
};
function roundOffsetsByDPR(_ref, win) {
  var x = _ref.x, y = _ref.y;
  var dpr = win.devicePixelRatio || 1;
  return {
    x: round(x * dpr) / dpr || 0,
    y: round(y * dpr) / dpr || 0
  };
}
function mapToStyles(_ref2) {
  var _Object$assign2;
  var popper2 = _ref2.popper, popperRect = _ref2.popperRect, placement = _ref2.placement, variation = _ref2.variation, offsets = _ref2.offsets, position = _ref2.position, gpuAcceleration = _ref2.gpuAcceleration, adaptive = _ref2.adaptive, roundOffsets = _ref2.roundOffsets, isFixed = _ref2.isFixed;
  var _offsets$x = offsets.x, x = _offsets$x === void 0 ? 0 : _offsets$x, _offsets$y = offsets.y, y = _offsets$y === void 0 ? 0 : _offsets$y;
  var _ref3 = typeof roundOffsets === "function" ? roundOffsets({
    x,
    y
  }) : {
    x,
    y
  };
  x = _ref3.x;
  y = _ref3.y;
  var hasX = offsets.hasOwnProperty("x");
  var hasY = offsets.hasOwnProperty("y");
  var sideX = left;
  var sideY = top;
  var win = window;
  if (adaptive) {
    var offsetParent = getOffsetParent(popper2);
    var heightProp = "clientHeight";
    var widthProp = "clientWidth";
    if (offsetParent === getWindow(popper2)) {
      offsetParent = getDocumentElement(popper2);
      if (getComputedStyle(offsetParent).position !== "static" && position === "absolute") {
        heightProp = "scrollHeight";
        widthProp = "scrollWidth";
      }
    }
    offsetParent = offsetParent;
    if (placement === top || (placement === left || placement === right) && variation === end) {
      sideY = bottom;
      var offsetY = isFixed && offsetParent === win && win.visualViewport ? win.visualViewport.height : (
        // $FlowFixMe[prop-missing]
        offsetParent[heightProp]
      );
      y -= offsetY - popperRect.height;
      y *= gpuAcceleration ? 1 : -1;
    }
    if (placement === left || (placement === top || placement === bottom) && variation === end) {
      sideX = right;
      var offsetX = isFixed && offsetParent === win && win.visualViewport ? win.visualViewport.width : (
        // $FlowFixMe[prop-missing]
        offsetParent[widthProp]
      );
      x -= offsetX - popperRect.width;
      x *= gpuAcceleration ? 1 : -1;
    }
  }
  var commonStyles = Object.assign({
    position
  }, adaptive && unsetSides);
  var _ref4 = roundOffsets === true ? roundOffsetsByDPR({
    x,
    y
  }, getWindow(popper2)) : {
    x,
    y
  };
  x = _ref4.x;
  y = _ref4.y;
  if (gpuAcceleration) {
    var _Object$assign;
    return Object.assign({}, commonStyles, (_Object$assign = {}, _Object$assign[sideY] = hasY ? "0" : "", _Object$assign[sideX] = hasX ? "0" : "", _Object$assign.transform = (win.devicePixelRatio || 1) <= 1 ? "translate(" + x + "px, " + y + "px)" : "translate3d(" + x + "px, " + y + "px, 0)", _Object$assign));
  }
  return Object.assign({}, commonStyles, (_Object$assign2 = {}, _Object$assign2[sideY] = hasY ? y + "px" : "", _Object$assign2[sideX] = hasX ? x + "px" : "", _Object$assign2.transform = "", _Object$assign2));
}
function computeStyles(_ref5) {
  var state = _ref5.state, options = _ref5.options;
  var _options$gpuAccelerat = options.gpuAcceleration, gpuAcceleration = _options$gpuAccelerat === void 0 ? true : _options$gpuAccelerat, _options$adaptive = options.adaptive, adaptive = _options$adaptive === void 0 ? true : _options$adaptive, _options$roundOffsets = options.roundOffsets, roundOffsets = _options$roundOffsets === void 0 ? true : _options$roundOffsets;
  var commonStyles = {
    placement: getBasePlacement(state.placement),
    variation: getVariation(state.placement),
    popper: state.elements.popper,
    popperRect: state.rects.popper,
    gpuAcceleration,
    isFixed: state.options.strategy === "fixed"
  };
  if (state.modifiersData.popperOffsets != null) {
    state.styles.popper = Object.assign({}, state.styles.popper, mapToStyles(Object.assign({}, commonStyles, {
      offsets: state.modifiersData.popperOffsets,
      position: state.options.strategy,
      adaptive,
      roundOffsets
    })));
  }
  if (state.modifiersData.arrow != null) {
    state.styles.arrow = Object.assign({}, state.styles.arrow, mapToStyles(Object.assign({}, commonStyles, {
      offsets: state.modifiersData.arrow,
      position: "absolute",
      adaptive: false,
      roundOffsets
    })));
  }
  state.attributes.popper = Object.assign({}, state.attributes.popper, {
    "data-popper-placement": state.placement
  });
}
var computeStyles$1 = {
  name: "computeStyles",
  enabled: true,
  phase: "beforeWrite",
  fn: computeStyles,
  data: {}
};
var passive = {
  passive: true
};
function effect(_ref) {
  var state = _ref.state, instance = _ref.instance, options = _ref.options;
  var _options$scroll = options.scroll, scroll = _options$scroll === void 0 ? true : _options$scroll, _options$resize = options.resize, resize = _options$resize === void 0 ? true : _options$resize;
  var window2 = getWindow(state.elements.popper);
  var scrollParents = [].concat(state.scrollParents.reference, state.scrollParents.popper);
  if (scroll) {
    scrollParents.forEach(function(scrollParent) {
      scrollParent.addEventListener("scroll", instance.update, passive);
    });
  }
  if (resize) {
    window2.addEventListener("resize", instance.update, passive);
  }
  return function() {
    if (scroll) {
      scrollParents.forEach(function(scrollParent) {
        scrollParent.removeEventListener("scroll", instance.update, passive);
      });
    }
    if (resize) {
      window2.removeEventListener("resize", instance.update, passive);
    }
  };
}
var eventListeners = {
  name: "eventListeners",
  enabled: true,
  phase: "write",
  fn: function fn() {
  },
  effect,
  data: {}
};
var hash$1 = {
  left: "right",
  right: "left",
  bottom: "top",
  top: "bottom"
};
function getOppositePlacement(placement) {
  return placement.replace(/left|right|bottom|top/g, function(matched) {
    return hash$1[matched];
  });
}
var hash = {
  start: "end",
  end: "start"
};
function getOppositeVariationPlacement(placement) {
  return placement.replace(/start|end/g, function(matched) {
    return hash[matched];
  });
}
function getWindowScroll(node) {
  var win = getWindow(node);
  var scrollLeft = win.pageXOffset;
  var scrollTop = win.pageYOffset;
  return {
    scrollLeft,
    scrollTop
  };
}
function getWindowScrollBarX(element) {
  return getBoundingClientRect(getDocumentElement(element)).left + getWindowScroll(element).scrollLeft;
}
function getViewportRect(element, strategy) {
  var win = getWindow(element);
  var html = getDocumentElement(element);
  var visualViewport = win.visualViewport;
  var width = html.clientWidth;
  var height = html.clientHeight;
  var x = 0;
  var y = 0;
  if (visualViewport) {
    width = visualViewport.width;
    height = visualViewport.height;
    var layoutViewport = isLayoutViewport();
    if (layoutViewport || !layoutViewport && strategy === "fixed") {
      x = visualViewport.offsetLeft;
      y = visualViewport.offsetTop;
    }
  }
  return {
    width,
    height,
    x: x + getWindowScrollBarX(element),
    y
  };
}
function getDocumentRect(element) {
  var _element$ownerDocumen;
  var html = getDocumentElement(element);
  var winScroll = getWindowScroll(element);
  var body = (_element$ownerDocumen = element.ownerDocument) == null ? void 0 : _element$ownerDocumen.body;
  var width = max(html.scrollWidth, html.clientWidth, body ? body.scrollWidth : 0, body ? body.clientWidth : 0);
  var height = max(html.scrollHeight, html.clientHeight, body ? body.scrollHeight : 0, body ? body.clientHeight : 0);
  var x = -winScroll.scrollLeft + getWindowScrollBarX(element);
  var y = -winScroll.scrollTop;
  if (getComputedStyle(body || html).direction === "rtl") {
    x += max(html.clientWidth, body ? body.clientWidth : 0) - width;
  }
  return {
    width,
    height,
    x,
    y
  };
}
function isScrollParent(element) {
  var _getComputedStyle = getComputedStyle(element), overflow = _getComputedStyle.overflow, overflowX = _getComputedStyle.overflowX, overflowY = _getComputedStyle.overflowY;
  return /auto|scroll|overlay|hidden/.test(overflow + overflowY + overflowX);
}
function getScrollParent(node) {
  if (["html", "body", "#document"].indexOf(getNodeName(node)) >= 0) {
    return node.ownerDocument.body;
  }
  if (isHTMLElement(node) && isScrollParent(node)) {
    return node;
  }
  return getScrollParent(getParentNode(node));
}
function listScrollParents(element, list) {
  var _element$ownerDocumen;
  if (list === void 0) {
    list = [];
  }
  var scrollParent = getScrollParent(element);
  var isBody = scrollParent === ((_element$ownerDocumen = element.ownerDocument) == null ? void 0 : _element$ownerDocumen.body);
  var win = getWindow(scrollParent);
  var target = isBody ? [win].concat(win.visualViewport || [], isScrollParent(scrollParent) ? scrollParent : []) : scrollParent;
  var updatedList = list.concat(target);
  return isBody ? updatedList : (
    // $FlowFixMe[incompatible-call]: isBody tells us target will be an HTMLElement here
    updatedList.concat(listScrollParents(getParentNode(target)))
  );
}
function rectToClientRect(rect) {
  return Object.assign({}, rect, {
    left: rect.x,
    top: rect.y,
    right: rect.x + rect.width,
    bottom: rect.y + rect.height
  });
}
function getInnerBoundingClientRect(element, strategy) {
  var rect = getBoundingClientRect(element, false, strategy === "fixed");
  rect.top = rect.top + element.clientTop;
  rect.left = rect.left + element.clientLeft;
  rect.bottom = rect.top + element.clientHeight;
  rect.right = rect.left + element.clientWidth;
  rect.width = element.clientWidth;
  rect.height = element.clientHeight;
  rect.x = rect.left;
  rect.y = rect.top;
  return rect;
}
function getClientRectFromMixedType(element, clippingParent, strategy) {
  return clippingParent === viewport ? rectToClientRect(getViewportRect(element, strategy)) : isElement(clippingParent) ? getInnerBoundingClientRect(clippingParent, strategy) : rectToClientRect(getDocumentRect(getDocumentElement(element)));
}
function getClippingParents(element) {
  var clippingParents2 = listScrollParents(getParentNode(element));
  var canEscapeClipping = ["absolute", "fixed"].indexOf(getComputedStyle(element).position) >= 0;
  var clipperElement = canEscapeClipping && isHTMLElement(element) ? getOffsetParent(element) : element;
  if (!isElement(clipperElement)) {
    return [];
  }
  return clippingParents2.filter(function(clippingParent) {
    return isElement(clippingParent) && contains(clippingParent, clipperElement) && getNodeName(clippingParent) !== "body";
  });
}
function getClippingRect(element, boundary, rootBoundary, strategy) {
  var mainClippingParents = boundary === "clippingParents" ? getClippingParents(element) : [].concat(boundary);
  var clippingParents2 = [].concat(mainClippingParents, [rootBoundary]);
  var firstClippingParent = clippingParents2[0];
  var clippingRect = clippingParents2.reduce(function(accRect, clippingParent) {
    var rect = getClientRectFromMixedType(element, clippingParent, strategy);
    accRect.top = max(rect.top, accRect.top);
    accRect.right = min(rect.right, accRect.right);
    accRect.bottom = min(rect.bottom, accRect.bottom);
    accRect.left = max(rect.left, accRect.left);
    return accRect;
  }, getClientRectFromMixedType(element, firstClippingParent, strategy));
  clippingRect.width = clippingRect.right - clippingRect.left;
  clippingRect.height = clippingRect.bottom - clippingRect.top;
  clippingRect.x = clippingRect.left;
  clippingRect.y = clippingRect.top;
  return clippingRect;
}
function computeOffsets(_ref) {
  var reference2 = _ref.reference, element = _ref.element, placement = _ref.placement;
  var basePlacement = placement ? getBasePlacement(placement) : null;
  var variation = placement ? getVariation(placement) : null;
  var commonX = reference2.x + reference2.width / 2 - element.width / 2;
  var commonY = reference2.y + reference2.height / 2 - element.height / 2;
  var offsets;
  switch (basePlacement) {
    case top:
      offsets = {
        x: commonX,
        y: reference2.y - element.height
      };
      break;
    case bottom:
      offsets = {
        x: commonX,
        y: reference2.y + reference2.height
      };
      break;
    case right:
      offsets = {
        x: reference2.x + reference2.width,
        y: commonY
      };
      break;
    case left:
      offsets = {
        x: reference2.x - element.width,
        y: commonY
      };
      break;
    default:
      offsets = {
        x: reference2.x,
        y: reference2.y
      };
  }
  var mainAxis = basePlacement ? getMainAxisFromPlacement(basePlacement) : null;
  if (mainAxis != null) {
    var len = mainAxis === "y" ? "height" : "width";
    switch (variation) {
      case start:
        offsets[mainAxis] = offsets[mainAxis] - (reference2[len] / 2 - element[len] / 2);
        break;
      case end:
        offsets[mainAxis] = offsets[mainAxis] + (reference2[len] / 2 - element[len] / 2);
        break;
    }
  }
  return offsets;
}
function detectOverflow(state, options) {
  if (options === void 0) {
    options = {};
  }
  var _options = options, _options$placement = _options.placement, placement = _options$placement === void 0 ? state.placement : _options$placement, _options$strategy = _options.strategy, strategy = _options$strategy === void 0 ? state.strategy : _options$strategy, _options$boundary = _options.boundary, boundary = _options$boundary === void 0 ? clippingParents : _options$boundary, _options$rootBoundary = _options.rootBoundary, rootBoundary = _options$rootBoundary === void 0 ? viewport : _options$rootBoundary, _options$elementConte = _options.elementContext, elementContext = _options$elementConte === void 0 ? popper : _options$elementConte, _options$altBoundary = _options.altBoundary, altBoundary = _options$altBoundary === void 0 ? false : _options$altBoundary, _options$padding = _options.padding, padding = _options$padding === void 0 ? 0 : _options$padding;
  var paddingObject = mergePaddingObject(typeof padding !== "number" ? padding : expandToHashMap(padding, basePlacements));
  var altContext = elementContext === popper ? reference : popper;
  var popperRect = state.rects.popper;
  var element = state.elements[altBoundary ? altContext : elementContext];
  var clippingClientRect = getClippingRect(isElement(element) ? element : element.contextElement || getDocumentElement(state.elements.popper), boundary, rootBoundary, strategy);
  var referenceClientRect = getBoundingClientRect(state.elements.reference);
  var popperOffsets2 = computeOffsets({
    reference: referenceClientRect,
    element: popperRect,
    placement
  });
  var popperClientRect = rectToClientRect(Object.assign({}, popperRect, popperOffsets2));
  var elementClientRect = elementContext === popper ? popperClientRect : referenceClientRect;
  var overflowOffsets = {
    top: clippingClientRect.top - elementClientRect.top + paddingObject.top,
    bottom: elementClientRect.bottom - clippingClientRect.bottom + paddingObject.bottom,
    left: clippingClientRect.left - elementClientRect.left + paddingObject.left,
    right: elementClientRect.right - clippingClientRect.right + paddingObject.right
  };
  var offsetData = state.modifiersData.offset;
  if (elementContext === popper && offsetData) {
    var offset2 = offsetData[placement];
    Object.keys(overflowOffsets).forEach(function(key) {
      var multiply = [right, bottom].indexOf(key) >= 0 ? 1 : -1;
      var axis = [top, bottom].indexOf(key) >= 0 ? "y" : "x";
      overflowOffsets[key] += offset2[axis] * multiply;
    });
  }
  return overflowOffsets;
}
function computeAutoPlacement(state, options) {
  if (options === void 0) {
    options = {};
  }
  var _options = options, placement = _options.placement, boundary = _options.boundary, rootBoundary = _options.rootBoundary, padding = _options.padding, flipVariations = _options.flipVariations, _options$allowedAutoP = _options.allowedAutoPlacements, allowedAutoPlacements = _options$allowedAutoP === void 0 ? placements : _options$allowedAutoP;
  var variation = getVariation(placement);
  var placements$1 = variation ? flipVariations ? variationPlacements : variationPlacements.filter(function(placement2) {
    return getVariation(placement2) === variation;
  }) : basePlacements;
  var allowedPlacements = placements$1.filter(function(placement2) {
    return allowedAutoPlacements.indexOf(placement2) >= 0;
  });
  if (allowedPlacements.length === 0) {
    allowedPlacements = placements$1;
  }
  var overflows = allowedPlacements.reduce(function(acc, placement2) {
    acc[placement2] = detectOverflow(state, {
      placement: placement2,
      boundary,
      rootBoundary,
      padding
    })[getBasePlacement(placement2)];
    return acc;
  }, {});
  return Object.keys(overflows).sort(function(a, b) {
    return overflows[a] - overflows[b];
  });
}
function getExpandedFallbackPlacements(placement) {
  if (getBasePlacement(placement) === auto) {
    return [];
  }
  var oppositePlacement = getOppositePlacement(placement);
  return [getOppositeVariationPlacement(placement), oppositePlacement, getOppositeVariationPlacement(oppositePlacement)];
}
function flip(_ref) {
  var state = _ref.state, options = _ref.options, name = _ref.name;
  if (state.modifiersData[name]._skip) {
    return;
  }
  var _options$mainAxis = options.mainAxis, checkMainAxis = _options$mainAxis === void 0 ? true : _options$mainAxis, _options$altAxis = options.altAxis, checkAltAxis = _options$altAxis === void 0 ? true : _options$altAxis, specifiedFallbackPlacements = options.fallbackPlacements, padding = options.padding, boundary = options.boundary, rootBoundary = options.rootBoundary, altBoundary = options.altBoundary, _options$flipVariatio = options.flipVariations, flipVariations = _options$flipVariatio === void 0 ? true : _options$flipVariatio, allowedAutoPlacements = options.allowedAutoPlacements;
  var preferredPlacement = state.options.placement;
  var basePlacement = getBasePlacement(preferredPlacement);
  var isBasePlacement = basePlacement === preferredPlacement;
  var fallbackPlacements = specifiedFallbackPlacements || (isBasePlacement || !flipVariations ? [getOppositePlacement(preferredPlacement)] : getExpandedFallbackPlacements(preferredPlacement));
  var placements2 = [preferredPlacement].concat(fallbackPlacements).reduce(function(acc, placement2) {
    return acc.concat(getBasePlacement(placement2) === auto ? computeAutoPlacement(state, {
      placement: placement2,
      boundary,
      rootBoundary,
      padding,
      flipVariations,
      allowedAutoPlacements
    }) : placement2);
  }, []);
  var referenceRect = state.rects.reference;
  var popperRect = state.rects.popper;
  var checksMap = /* @__PURE__ */ new Map();
  var makeFallbackChecks = true;
  var firstFittingPlacement = placements2[0];
  for (var i = 0; i < placements2.length; i++) {
    var placement = placements2[i];
    var _basePlacement = getBasePlacement(placement);
    var isStartVariation = getVariation(placement) === start;
    var isVertical = [top, bottom].indexOf(_basePlacement) >= 0;
    var len = isVertical ? "width" : "height";
    var overflow = detectOverflow(state, {
      placement,
      boundary,
      rootBoundary,
      altBoundary,
      padding
    });
    var mainVariationSide = isVertical ? isStartVariation ? right : left : isStartVariation ? bottom : top;
    if (referenceRect[len] > popperRect[len]) {
      mainVariationSide = getOppositePlacement(mainVariationSide);
    }
    var altVariationSide = getOppositePlacement(mainVariationSide);
    var checks = [];
    if (checkMainAxis) {
      checks.push(overflow[_basePlacement] <= 0);
    }
    if (checkAltAxis) {
      checks.push(overflow[mainVariationSide] <= 0, overflow[altVariationSide] <= 0);
    }
    if (checks.every(function(check) {
      return check;
    })) {
      firstFittingPlacement = placement;
      makeFallbackChecks = false;
      break;
    }
    checksMap.set(placement, checks);
  }
  if (makeFallbackChecks) {
    var numberOfChecks = flipVariations ? 3 : 1;
    var _loop = function _loop2(_i2) {
      var fittingPlacement = placements2.find(function(placement2) {
        var checks2 = checksMap.get(placement2);
        if (checks2) {
          return checks2.slice(0, _i2).every(function(check) {
            return check;
          });
        }
      });
      if (fittingPlacement) {
        firstFittingPlacement = fittingPlacement;
        return "break";
      }
    };
    for (var _i = numberOfChecks; _i > 0; _i--) {
      var _ret = _loop(_i);
      if (_ret === "break") break;
    }
  }
  if (state.placement !== firstFittingPlacement) {
    state.modifiersData[name]._skip = true;
    state.placement = firstFittingPlacement;
    state.reset = true;
  }
}
var flip$1 = {
  name: "flip",
  enabled: true,
  phase: "main",
  fn: flip,
  requiresIfExists: ["offset"],
  data: {
    _skip: false
  }
};
function getSideOffsets(overflow, rect, preventedOffsets) {
  if (preventedOffsets === void 0) {
    preventedOffsets = {
      x: 0,
      y: 0
    };
  }
  return {
    top: overflow.top - rect.height - preventedOffsets.y,
    right: overflow.right - rect.width + preventedOffsets.x,
    bottom: overflow.bottom - rect.height + preventedOffsets.y,
    left: overflow.left - rect.width - preventedOffsets.x
  };
}
function isAnySideFullyClipped(overflow) {
  return [top, right, bottom, left].some(function(side) {
    return overflow[side] >= 0;
  });
}
function hide(_ref) {
  var state = _ref.state, name = _ref.name;
  var referenceRect = state.rects.reference;
  var popperRect = state.rects.popper;
  var preventedOffsets = state.modifiersData.preventOverflow;
  var referenceOverflow = detectOverflow(state, {
    elementContext: "reference"
  });
  var popperAltOverflow = detectOverflow(state, {
    altBoundary: true
  });
  var referenceClippingOffsets = getSideOffsets(referenceOverflow, referenceRect);
  var popperEscapeOffsets = getSideOffsets(popperAltOverflow, popperRect, preventedOffsets);
  var isReferenceHidden = isAnySideFullyClipped(referenceClippingOffsets);
  var hasPopperEscaped = isAnySideFullyClipped(popperEscapeOffsets);
  state.modifiersData[name] = {
    referenceClippingOffsets,
    popperEscapeOffsets,
    isReferenceHidden,
    hasPopperEscaped
  };
  state.attributes.popper = Object.assign({}, state.attributes.popper, {
    "data-popper-reference-hidden": isReferenceHidden,
    "data-popper-escaped": hasPopperEscaped
  });
}
var hide$1 = {
  name: "hide",
  enabled: true,
  phase: "main",
  requiresIfExists: ["preventOverflow"],
  fn: hide
};
function distanceAndSkiddingToXY(placement, rects, offset2) {
  var basePlacement = getBasePlacement(placement);
  var invertDistance = [left, top].indexOf(basePlacement) >= 0 ? -1 : 1;
  var _ref = typeof offset2 === "function" ? offset2(Object.assign({}, rects, {
    placement
  })) : offset2, skidding = _ref[0], distance = _ref[1];
  skidding = skidding || 0;
  distance = (distance || 0) * invertDistance;
  return [left, right].indexOf(basePlacement) >= 0 ? {
    x: distance,
    y: skidding
  } : {
    x: skidding,
    y: distance
  };
}
function offset(_ref2) {
  var state = _ref2.state, options = _ref2.options, name = _ref2.name;
  var _options$offset = options.offset, offset2 = _options$offset === void 0 ? [0, 0] : _options$offset;
  var data = placements.reduce(function(acc, placement) {
    acc[placement] = distanceAndSkiddingToXY(placement, state.rects, offset2);
    return acc;
  }, {});
  var _data$state$placement = data[state.placement], x = _data$state$placement.x, y = _data$state$placement.y;
  if (state.modifiersData.popperOffsets != null) {
    state.modifiersData.popperOffsets.x += x;
    state.modifiersData.popperOffsets.y += y;
  }
  state.modifiersData[name] = data;
}
var offset$1 = {
  name: "offset",
  enabled: true,
  phase: "main",
  requires: ["popperOffsets"],
  fn: offset
};
function popperOffsets(_ref) {
  var state = _ref.state, name = _ref.name;
  state.modifiersData[name] = computeOffsets({
    reference: state.rects.reference,
    element: state.rects.popper,
    placement: state.placement
  });
}
var popperOffsets$1 = {
  name: "popperOffsets",
  enabled: true,
  phase: "read",
  fn: popperOffsets,
  data: {}
};
function getAltAxis(axis) {
  return axis === "x" ? "y" : "x";
}
function preventOverflow(_ref) {
  var state = _ref.state, options = _ref.options, name = _ref.name;
  var _options$mainAxis = options.mainAxis, checkMainAxis = _options$mainAxis === void 0 ? true : _options$mainAxis, _options$altAxis = options.altAxis, checkAltAxis = _options$altAxis === void 0 ? false : _options$altAxis, boundary = options.boundary, rootBoundary = options.rootBoundary, altBoundary = options.altBoundary, padding = options.padding, _options$tether = options.tether, tether = _options$tether === void 0 ? true : _options$tether, _options$tetherOffset = options.tetherOffset, tetherOffset = _options$tetherOffset === void 0 ? 0 : _options$tetherOffset;
  var overflow = detectOverflow(state, {
    boundary,
    rootBoundary,
    padding,
    altBoundary
  });
  var basePlacement = getBasePlacement(state.placement);
  var variation = getVariation(state.placement);
  var isBasePlacement = !variation;
  var mainAxis = getMainAxisFromPlacement(basePlacement);
  var altAxis = getAltAxis(mainAxis);
  var popperOffsets2 = state.modifiersData.popperOffsets;
  var referenceRect = state.rects.reference;
  var popperRect = state.rects.popper;
  var tetherOffsetValue = typeof tetherOffset === "function" ? tetherOffset(Object.assign({}, state.rects, {
    placement: state.placement
  })) : tetherOffset;
  var normalizedTetherOffsetValue = typeof tetherOffsetValue === "number" ? {
    mainAxis: tetherOffsetValue,
    altAxis: tetherOffsetValue
  } : Object.assign({
    mainAxis: 0,
    altAxis: 0
  }, tetherOffsetValue);
  var offsetModifierState = state.modifiersData.offset ? state.modifiersData.offset[state.placement] : null;
  var data = {
    x: 0,
    y: 0
  };
  if (!popperOffsets2) {
    return;
  }
  if (checkMainAxis) {
    var _offsetModifierState$;
    var mainSide = mainAxis === "y" ? top : left;
    var altSide = mainAxis === "y" ? bottom : right;
    var len = mainAxis === "y" ? "height" : "width";
    var offset2 = popperOffsets2[mainAxis];
    var min$1 = offset2 + overflow[mainSide];
    var max$1 = offset2 - overflow[altSide];
    var additive = tether ? -popperRect[len] / 2 : 0;
    var minLen = variation === start ? referenceRect[len] : popperRect[len];
    var maxLen = variation === start ? -popperRect[len] : -referenceRect[len];
    var arrowElement = state.elements.arrow;
    var arrowRect = tether && arrowElement ? getLayoutRect(arrowElement) : {
      width: 0,
      height: 0
    };
    var arrowPaddingObject = state.modifiersData["arrow#persistent"] ? state.modifiersData["arrow#persistent"].padding : getFreshSideObject();
    var arrowPaddingMin = arrowPaddingObject[mainSide];
    var arrowPaddingMax = arrowPaddingObject[altSide];
    var arrowLen = within(0, referenceRect[len], arrowRect[len]);
    var minOffset = isBasePlacement ? referenceRect[len] / 2 - additive - arrowLen - arrowPaddingMin - normalizedTetherOffsetValue.mainAxis : minLen - arrowLen - arrowPaddingMin - normalizedTetherOffsetValue.mainAxis;
    var maxOffset = isBasePlacement ? -referenceRect[len] / 2 + additive + arrowLen + arrowPaddingMax + normalizedTetherOffsetValue.mainAxis : maxLen + arrowLen + arrowPaddingMax + normalizedTetherOffsetValue.mainAxis;
    var arrowOffsetParent = state.elements.arrow && getOffsetParent(state.elements.arrow);
    var clientOffset = arrowOffsetParent ? mainAxis === "y" ? arrowOffsetParent.clientTop || 0 : arrowOffsetParent.clientLeft || 0 : 0;
    var offsetModifierValue = (_offsetModifierState$ = offsetModifierState == null ? void 0 : offsetModifierState[mainAxis]) != null ? _offsetModifierState$ : 0;
    var tetherMin = offset2 + minOffset - offsetModifierValue - clientOffset;
    var tetherMax = offset2 + maxOffset - offsetModifierValue;
    var preventedOffset = within(tether ? min(min$1, tetherMin) : min$1, offset2, tether ? max(max$1, tetherMax) : max$1);
    popperOffsets2[mainAxis] = preventedOffset;
    data[mainAxis] = preventedOffset - offset2;
  }
  if (checkAltAxis) {
    var _offsetModifierState$2;
    var _mainSide = mainAxis === "x" ? top : left;
    var _altSide = mainAxis === "x" ? bottom : right;
    var _offset = popperOffsets2[altAxis];
    var _len = altAxis === "y" ? "height" : "width";
    var _min = _offset + overflow[_mainSide];
    var _max = _offset - overflow[_altSide];
    var isOriginSide = [top, left].indexOf(basePlacement) !== -1;
    var _offsetModifierValue = (_offsetModifierState$2 = offsetModifierState == null ? void 0 : offsetModifierState[altAxis]) != null ? _offsetModifierState$2 : 0;
    var _tetherMin = isOriginSide ? _min : _offset - referenceRect[_len] - popperRect[_len] - _offsetModifierValue + normalizedTetherOffsetValue.altAxis;
    var _tetherMax = isOriginSide ? _offset + referenceRect[_len] + popperRect[_len] - _offsetModifierValue - normalizedTetherOffsetValue.altAxis : _max;
    var _preventedOffset = tether && isOriginSide ? withinMaxClamp(_tetherMin, _offset, _tetherMax) : within(tether ? _tetherMin : _min, _offset, tether ? _tetherMax : _max);
    popperOffsets2[altAxis] = _preventedOffset;
    data[altAxis] = _preventedOffset - _offset;
  }
  state.modifiersData[name] = data;
}
var preventOverflow$1 = {
  name: "preventOverflow",
  enabled: true,
  phase: "main",
  fn: preventOverflow,
  requiresIfExists: ["offset"]
};
function getHTMLElementScroll(element) {
  return {
    scrollLeft: element.scrollLeft,
    scrollTop: element.scrollTop
  };
}
function getNodeScroll(node) {
  if (node === getWindow(node) || !isHTMLElement(node)) {
    return getWindowScroll(node);
  } else {
    return getHTMLElementScroll(node);
  }
}
function isElementScaled(element) {
  var rect = element.getBoundingClientRect();
  var scaleX = round(rect.width) / element.offsetWidth || 1;
  var scaleY = round(rect.height) / element.offsetHeight || 1;
  return scaleX !== 1 || scaleY !== 1;
}
function getCompositeRect(elementOrVirtualElement, offsetParent, isFixed) {
  if (isFixed === void 0) {
    isFixed = false;
  }
  var isOffsetParentAnElement = isHTMLElement(offsetParent);
  var offsetParentIsScaled = isHTMLElement(offsetParent) && isElementScaled(offsetParent);
  var documentElement = getDocumentElement(offsetParent);
  var rect = getBoundingClientRect(elementOrVirtualElement, offsetParentIsScaled, isFixed);
  var scroll = {
    scrollLeft: 0,
    scrollTop: 0
  };
  var offsets = {
    x: 0,
    y: 0
  };
  if (isOffsetParentAnElement || !isOffsetParentAnElement && !isFixed) {
    if (getNodeName(offsetParent) !== "body" || // https://github.com/popperjs/popper-core/issues/1078
    isScrollParent(documentElement)) {
      scroll = getNodeScroll(offsetParent);
    }
    if (isHTMLElement(offsetParent)) {
      offsets = getBoundingClientRect(offsetParent, true);
      offsets.x += offsetParent.clientLeft;
      offsets.y += offsetParent.clientTop;
    } else if (documentElement) {
      offsets.x = getWindowScrollBarX(documentElement);
    }
  }
  return {
    x: rect.left + scroll.scrollLeft - offsets.x,
    y: rect.top + scroll.scrollTop - offsets.y,
    width: rect.width,
    height: rect.height
  };
}
function order(modifiers) {
  var map = /* @__PURE__ */ new Map();
  var visited = /* @__PURE__ */ new Set();
  var result = [];
  modifiers.forEach(function(modifier) {
    map.set(modifier.name, modifier);
  });
  function sort(modifier) {
    visited.add(modifier.name);
    var requires = [].concat(modifier.requires || [], modifier.requiresIfExists || []);
    requires.forEach(function(dep) {
      if (!visited.has(dep)) {
        var depModifier = map.get(dep);
        if (depModifier) {
          sort(depModifier);
        }
      }
    });
    result.push(modifier);
  }
  modifiers.forEach(function(modifier) {
    if (!visited.has(modifier.name)) {
      sort(modifier);
    }
  });
  return result;
}
function orderModifiers(modifiers) {
  var orderedModifiers = order(modifiers);
  return modifierPhases.reduce(function(acc, phase) {
    return acc.concat(orderedModifiers.filter(function(modifier) {
      return modifier.phase === phase;
    }));
  }, []);
}
function debounce(fn2) {
  var pending;
  return function() {
    if (!pending) {
      pending = new Promise(function(resolve) {
        Promise.resolve().then(function() {
          pending = void 0;
          resolve(fn2());
        });
      });
    }
    return pending;
  };
}
function mergeByName(modifiers) {
  var merged = modifiers.reduce(function(merged2, current) {
    var existing = merged2[current.name];
    merged2[current.name] = existing ? Object.assign({}, existing, current, {
      options: Object.assign({}, existing.options, current.options),
      data: Object.assign({}, existing.data, current.data)
    }) : current;
    return merged2;
  }, {});
  return Object.keys(merged).map(function(key) {
    return merged[key];
  });
}
var DEFAULT_OPTIONS = {
  placement: "bottom",
  modifiers: [],
  strategy: "absolute"
};
function areValidElements() {
  for (var _len = arguments.length, args = new Array(_len), _key = 0; _key < _len; _key++) {
    args[_key] = arguments[_key];
  }
  return !args.some(function(element) {
    return !(element && typeof element.getBoundingClientRect === "function");
  });
}
function popperGenerator(generatorOptions) {
  if (generatorOptions === void 0) {
    generatorOptions = {};
  }
  var _generatorOptions = generatorOptions, _generatorOptions$def = _generatorOptions.defaultModifiers, defaultModifiers2 = _generatorOptions$def === void 0 ? [] : _generatorOptions$def, _generatorOptions$def2 = _generatorOptions.defaultOptions, defaultOptions = _generatorOptions$def2 === void 0 ? DEFAULT_OPTIONS : _generatorOptions$def2;
  return function createPopper2(reference2, popper2, options) {
    if (options === void 0) {
      options = defaultOptions;
    }
    var state = {
      placement: "bottom",
      orderedModifiers: [],
      options: Object.assign({}, DEFAULT_OPTIONS, defaultOptions),
      modifiersData: {},
      elements: {
        reference: reference2,
        popper: popper2
      },
      attributes: {},
      styles: {}
    };
    var effectCleanupFns = [];
    var isDestroyed = false;
    var instance = {
      state,
      setOptions: function setOptions(setOptionsAction) {
        var options2 = typeof setOptionsAction === "function" ? setOptionsAction(state.options) : setOptionsAction;
        cleanupModifierEffects();
        state.options = Object.assign({}, defaultOptions, state.options, options2);
        state.scrollParents = {
          reference: isElement(reference2) ? listScrollParents(reference2) : reference2.contextElement ? listScrollParents(reference2.contextElement) : [],
          popper: listScrollParents(popper2)
        };
        var orderedModifiers = orderModifiers(mergeByName([].concat(defaultModifiers2, state.options.modifiers)));
        state.orderedModifiers = orderedModifiers.filter(function(m) {
          return m.enabled;
        });
        runModifierEffects();
        return instance.update();
      },
      // Sync update – it will always be executed, even if not necessary. This
      // is useful for low frequency updates where sync behavior simplifies the
      // logic.
      // For high frequency updates (e.g. `resize` and `scroll` events), always
      // prefer the async Popper#update method
      forceUpdate: function forceUpdate() {
        if (isDestroyed) {
          return;
        }
        var _state$elements = state.elements, reference3 = _state$elements.reference, popper3 = _state$elements.popper;
        if (!areValidElements(reference3, popper3)) {
          return;
        }
        state.rects = {
          reference: getCompositeRect(reference3, getOffsetParent(popper3), state.options.strategy === "fixed"),
          popper: getLayoutRect(popper3)
        };
        state.reset = false;
        state.placement = state.options.placement;
        state.orderedModifiers.forEach(function(modifier) {
          return state.modifiersData[modifier.name] = Object.assign({}, modifier.data);
        });
        for (var index2 = 0; index2 < state.orderedModifiers.length; index2++) {
          if (state.reset === true) {
            state.reset = false;
            index2 = -1;
            continue;
          }
          var _state$orderedModifie = state.orderedModifiers[index2], fn2 = _state$orderedModifie.fn, _state$orderedModifie2 = _state$orderedModifie.options, _options = _state$orderedModifie2 === void 0 ? {} : _state$orderedModifie2, name = _state$orderedModifie.name;
          if (typeof fn2 === "function") {
            state = fn2({
              state,
              options: _options,
              name,
              instance
            }) || state;
          }
        }
      },
      // Async and optimistically optimized update – it will not be executed if
      // not necessary (debounced to run at most once-per-tick)
      update: debounce(function() {
        return new Promise(function(resolve) {
          instance.forceUpdate();
          resolve(state);
        });
      }),
      destroy: function destroy() {
        cleanupModifierEffects();
        isDestroyed = true;
      }
    };
    if (!areValidElements(reference2, popper2)) {
      return instance;
    }
    instance.setOptions(options).then(function(state2) {
      if (!isDestroyed && options.onFirstUpdate) {
        options.onFirstUpdate(state2);
      }
    });
    function runModifierEffects() {
      state.orderedModifiers.forEach(function(_ref) {
        var name = _ref.name, _ref$options = _ref.options, options2 = _ref$options === void 0 ? {} : _ref$options, effect2 = _ref.effect;
        if (typeof effect2 === "function") {
          var cleanupFn = effect2({
            state,
            name,
            instance,
            options: options2
          });
          var noopFn = function noopFn2() {
          };
          effectCleanupFns.push(cleanupFn || noopFn);
        }
      });
    }
    function cleanupModifierEffects() {
      effectCleanupFns.forEach(function(fn2) {
        return fn2();
      });
      effectCleanupFns = [];
    }
    return instance;
  };
}
var defaultModifiers = [eventListeners, popperOffsets$1, computeStyles$1, applyStyles$1, offset$1, flip$1, preventOverflow$1, arrow$1, hide$1];
var createPopper = popperGenerator({
  defaultModifiers
});
var initializedDropdowns = /* @__PURE__ */ new WeakSet();
var activeDropdowns = [];
var Dropdown$1 = class Dropdown {
  constructor(dropdownElement) {
    this.popperInstance = null;
    this.dropdown = dropdownElement;
    this.button = this.dropdown.querySelector('[data-toggle="dropdown"],[data-toggle="menu"]');
    this.menu = this.dropdown.querySelector('[data-role="menu"]');
    this.placement = this.dropdown.getAttribute("data-placement") || "bottom-start";
    this.init();
  }
  init() {
    return __awaiter(this, void 0, void 0, function* () {
      yield loadPopperJs();
      this.popperInstance = createPopper(this.button, this.menu, {
        placement: this.placement,
        modifiers: [{
          name: "offset",
          options: {
            offset: [0, 5]
          }
        }]
      });
      this.button.addEventListener("click", (e) => {
        e.stopPropagation();
        this.toggleDropdown();
      });
      document.addEventListener("click", (e) => {
        if (!this.dropdown.contains(e.target)) {
          this.closeDropdown();
        }
      });
      activeDropdowns.push({
        dropdown: this.dropdown,
        popperInstance: this.popperInstance
      });
    });
  }
  toggleDropdown() {
    const isExpanded = this.button.getAttribute("aria-expanded") === "true";
    isExpanded ? this.closeDropdown() : this.openDropdown();
  }
  openDropdown() {
    this.button.setAttribute("aria-expanded", "true");
    this.menu.hidden = false;
    this.menu.classList.remove("hidden");
    if (this.popperInstance) {
      this.popperInstance.update();
    }
  }
  closeDropdown() {
    this.button.setAttribute("aria-expanded", "false");
    this.menu.hidden = true;
    this.menu.classList.add("hidden");
  }
};
function initDropdowns() {
  document.querySelectorAll(".dropdown, .menu").forEach((dropdownElement) => {
    if (!initializedDropdowns.has(dropdownElement)) {
      new Dropdown$1(dropdownElement);
      initializedDropdowns.add(dropdownElement);
    }
  });
}
function cleanupDropdowns() {
  activeDropdowns.forEach(({
    dropdown,
    popperInstance
  }) => {
    if (popperInstance) popperInstance.destroy();
    if (dropdown) initializedDropdowns.delete(dropdown);
  });
  activeDropdowns = [];
}
function loadAndInitDropdowns() {
  return __awaiter(this, void 0, void 0, function* () {
    yield loadPopperJs();
    initDropdowns();
  });
}
if (typeof window !== "undefined" && typeof document !== "undefined") {
  document.addEventListener("DOMContentLoaded", () => {
    loadAndInitDropdowns();
    const observer = new MutationObserver(() => {
      initDropdowns();
    });
    observer.observe(document.body, {
      childList: true,
      subtree: true
    });
  });
}
var Dropdown2 = class {
  /**
   * Creates an instance of Dropdown.
   * @param reference - The element or selector to position the dropdown menu relative to.
   * @param menu - The menu element to display as the dropdown.
   * @param config - Configuration options for the dropdown.
   */
  constructor(reference2, menu, config) {
    var _a;
    this.popperInstance = null;
    this.isOpen = false;
    this.shouldIgnoreClick = false;
    this.referenceElement = this.resolveElement(reference2, "Reference element not found");
    this.menu = this.resolveElement(menu, "Menu element not found");
    this.config = {
      placement: config.placement || "bottom-start",
      closeOnOutsideClick: (_a = config.closeOnOutsideClick) !== null && _a !== void 0 ? _a : true,
      offset: config.offset || [0, 5]
    };
    this.documentClickHandler = this.handleDocumentClick.bind(this);
    this.init();
  }
  /**
   * Resolves an element from an HTMLElement or selector string.
   * @param elementOrSelector - HTMLElement or a selector string.
   * @param errorMessage - Error message if the element is not found.
   * @returns The resolved HTMLElement.
   */
  resolveElement(elementOrSelector, errorMessage) {
    if (typeof elementOrSelector === "string") {
      const resolvedElement = document.querySelector(elementOrSelector);
      if (!resolvedElement) throw new Error(errorMessage);
      return resolvedElement;
    } else if (elementOrSelector instanceof HTMLElement) {
      return elementOrSelector;
    }
    throw new Error(errorMessage);
  }
  /**
   * Handles document click events for outside clicks
   */
  handleDocumentClick(e) {
    if (this.shouldIgnoreClick) {
      this.shouldIgnoreClick = false;
      return;
    }
    if (!this.menu.contains(e.target) && !this.referenceElement.contains(e.target)) {
      this.close();
    }
  }
  /**
   * Initializes the Dropdown component.
   */
  init() {
    return __awaiter(this, void 0, void 0, function* () {
      yield loadPopperJs();
      this.popperInstance = createPopper(this.referenceElement, this.menu, {
        placement: this.config.placement,
        modifiers: [{
          name: "offset",
          options: {
            offset: this.config.offset
          }
        }]
      });
      if (this.config.closeOnOutsideClick) {
        document.addEventListener("click", this.documentClickHandler);
      }
    });
  }
  /**
   * Set the prevent outside click flag to true.
   */
  preventOutsideClick() {
    this.shouldIgnoreClick = true;
  }
  /**
   * Toggles the dropdown menu visibility.
   */
  toggle() {
    this.isOpen ? this.close() : this.open();
  }
  /**
   * Opens the dropdown menu programmatically.
   */
  open() {
    var _a;
    if (this.isOpen) return;
    this.menu.hidden = false;
    this.menu.classList.remove("hidden");
    (_a = this.popperInstance) === null || _a === void 0 ? void 0 : _a.update();
    this.isOpen = true;
  }
  /**
   * Closes the dropdown menu programmatically.
   */
  close() {
    if (!this.isOpen) return;
    this.menu.hidden = true;
    this.menu.classList.add("hidden");
    this.isOpen = false;
  }
  /**
   * Destroys the Dropdown instance and cleans up resources.
   */
  destroy() {
    var _a;
    (_a = this.popperInstance) === null || _a === void 0 ? void 0 : _a.destroy();
    this.popperInstance = null;
    document.removeEventListener("click", this.documentClickHandler);
  }
};
var initializedPopovers = /* @__PURE__ */ new WeakSet();
var activePopovers = [];
function initPopovers() {
  document.querySelectorAll("[data-toggle='popover']").forEach((trigger) => {
    var _a;
    if (initializedPopovers.has(trigger)) return;
    const placement = trigger.getAttribute("data-placement") || "top";
    const popoverClasses = trigger.getAttribute("data-popover-class") || "popover-default";
    const plainContent = trigger.getAttribute("data-popover-content");
    const isOpenByDefault = trigger.hasAttribute("data-open");
    let popoverInstance = null;
    let popperInstance = null;
    let popoverElement = null;
    let originalContentElement = null;
    const contentElement = ((_a = trigger.nextElementSibling) === null || _a === void 0 ? void 0 : _a.matches("[data-popover-content]")) ? trigger.nextElementSibling : null;
    function openPopover() {
      return __awaiter(this, void 0, void 0, function* () {
        yield loadPopperJs();
        popoverElement = document.createElement("div");
        popoverElement.className = popoverClasses;
        if (contentElement) {
          originalContentElement = contentElement.cloneNode(true);
          originalContentElement.classList.remove("hidden");
          popoverElement.appendChild(originalContentElement);
        } else if (plainContent) {
          popoverElement.textContent = plainContent;
        } else {
          console.error("No content provided for popover:", trigger);
          return;
        }
        document.body.appendChild(popoverElement);
        popoverInstance = createPopper(trigger, popoverElement, {
          placement,
          modifiers: [{
            name: "offset",
            options: {
              offset: [0, 8]
            }
          }]
        });
        requestAnimationFrame(() => {
          if (popoverElement) {
            popoverElement.style.opacity = "1";
            popoverElement.style.transform = "scale(1)";
            popoverInstance === null || popoverInstance === void 0 ? void 0 : popoverInstance.update();
          }
        });
        if (popoverInstance) {
          activePopovers.push({
            trigger,
            popoverElement,
            popperInstance
          });
        }
      });
    }
    function closePopover() {
      if (popoverInstance) {
        popoverInstance.destroy();
        popoverInstance = null;
      }
      if (popoverElement) {
        popoverElement.remove();
        popoverElement = null;
      }
      if (originalContentElement) {
        originalContentElement.classList.add("hidden");
      }
      activePopovers = activePopovers.filter((p) => p.trigger !== trigger);
    }
    trigger.addEventListener("click", (event) => {
      event.stopPropagation();
      if (popoverInstance) {
        closePopover();
      } else {
        openPopover();
      }
    });
    if (isOpenByDefault) {
      openPopover();
    }
    initializedPopovers.add(trigger);
  });
}
function cleanupPopovers() {
  activePopovers.forEach(({
    popoverElement,
    popperInstance
  }) => {
    if (popperInstance) popperInstance.destroy();
    if (popoverElement) popoverElement.remove();
  });
  activePopovers = [];
}
function loadAndInitPopovers() {
  return __awaiter(this, void 0, void 0, function* () {
    yield loadPopperJs();
    initPopovers();
  });
}
if (typeof window !== "undefined" && typeof document !== "undefined") {
  document.addEventListener("DOMContentLoaded", () => {
    loadAndInitPopovers();
    const observer = new MutationObserver(() => {
      initPopovers();
    });
    observer.observe(document.body, {
      childList: true,
      subtree: true
    });
  });
}
var Popover = class {
  /**
   * Creates an instance of Popover.
   * @param trigger - The element that triggers the popover.
   * @param config - Configuration options for the popover.
   */
  constructor(trigger, config) {
    this.popperInstance = null;
    this.popoverElement = null;
    this.trigger = trigger;
    this.config = {
      placement: config.placement || "top",
      popoverClass: config.popoverClass || "popover-default",
      content: config.content || "",
      openByDefault: config.openByDefault || false,
      offset: config.offset || [0, 8]
    };
    this.init();
  }
  /**
   * Initializes the Popover instance.
   */
  init() {
    return __awaiter(this, void 0, void 0, function* () {
      if (this.config.openByDefault) {
        yield this.open();
      }
      this.trigger.addEventListener("click", this.handleTriggerClick.bind(this));
    });
  }
  /**
   * Handles the click event on the trigger element.
   * @param event - The click event.
   */
  handleTriggerClick(event) {
    event.stopPropagation();
    this.toggle();
  }
  /**
   * Opens the popover programmatically.
   */
  open() {
    return __awaiter(this, void 0, void 0, function* () {
      if (this.popoverElement) return;
      yield loadPopperJs();
      this.popoverElement = document.createElement("div");
      this.popoverElement.className = this.config.popoverClass || "popover-default";
      if (typeof this.config.content === "string") {
        this.popoverElement.textContent = this.config.content;
      } else if (this.config.content instanceof HTMLElement) {
        this.popoverElement.appendChild(this.config.content);
      } else {
        console.error("Invalid content provided for popover:", this.trigger);
        return;
      }
      document.body.appendChild(this.popoverElement);
      this.popperInstance = createPopper(this.trigger, this.popoverElement, {
        placement: this.config.placement,
        modifiers: [{
          name: "offset",
          options: {
            offset: this.config.offset
          }
        }]
      });
      requestAnimationFrame(() => {
        var _a;
        if (this.popoverElement) {
          this.popoverElement.style.opacity = "1";
          this.popoverElement.style.transform = "scale(1)";
          (_a = this.popperInstance) === null || _a === void 0 ? void 0 : _a.update();
        }
      });
    });
  }
  /**
   * Closes the popover programmatically.
   */
  close() {
    if (!this.popperInstance || !this.popoverElement) return;
    this.popperInstance.destroy();
    this.popperInstance = null;
    this.popoverElement.remove();
    this.popoverElement = null;
  }
  /**
   * Toggles the popover's visibility programmatically.
   */
  toggle() {
    if (this.popoverElement) {
      this.close();
    } else {
      this.open();
    }
  }
  /**
   * Destroys the Popover instance and cleans up resources.
   */
  destroy() {
    this.close();
    this.trigger.removeEventListener("click", this.handleTriggerClick.bind(this));
  }
};
var initializedTooltips = /* @__PURE__ */ new WeakSet();
var activeTooltips = [];
function initTooltips() {
  document.querySelectorAll("[data-toggle='tooltip']").forEach((trigger) => {
    var _a;
    if (initializedTooltips.has(trigger)) return;
    const title = trigger.getAttribute("data-title") || "";
    const placement = trigger.getAttribute("data-placement") || "top";
    const tooltipClasses = trigger.getAttribute("data-tooltip-class") || "tooltip-default";
    let tooltipInstance = null;
    let tooltipElement = null;
    let customContentElement = null;
    if ((_a = trigger.nextElementSibling) === null || _a === void 0 ? void 0 : _a.matches("[data-tooltip-content]")) {
      customContentElement = trigger.nextElementSibling;
    }
    function showTooltip() {
      return __awaiter(this, void 0, void 0, function* () {
        if (tooltipElement) return;
        yield loadPopperJs();
        tooltipElement = document.createElement("div");
        tooltipElement.className = tooltipClasses;
        if (customContentElement) {
          const contentClone = customContentElement.cloneNode(true);
          contentClone.classList.remove("hidden");
          tooltipElement.appendChild(contentClone);
        } else if (title) {
          tooltipElement.textContent = title;
        } else {
          console.warn("No tooltip content provided for:", trigger);
          return;
        }
        document.body.appendChild(tooltipElement);
        tooltipInstance = createPopper(trigger, tooltipElement, {
          placement,
          modifiers: [{
            name: "offset",
            options: {
              offset: [0, 8]
            }
          }]
        });
        activeTooltips.push({
          trigger,
          tooltipElement,
          tooltipInstance
        });
      });
    }
    function hideTooltip() {
      if (tooltipInstance) {
        tooltipInstance.destroy();
        tooltipInstance = null;
      }
      if (tooltipElement) {
        tooltipElement.remove();
        tooltipElement = null;
      }
      activeTooltips = activeTooltips.filter((t) => t.trigger !== trigger);
    }
    trigger.addEventListener("mouseenter", showTooltip);
    trigger.addEventListener("mouseleave", hideTooltip);
    initializedTooltips.add(trigger);
  });
}
function cleanupTooltips() {
  activeTooltips.forEach(({
    tooltipElement,
    tooltipInstance
  }) => {
    if (tooltipInstance) tooltipInstance.destroy();
    if (tooltipElement) tooltipElement.remove();
  });
  activeTooltips = [];
}
function loadAndInitTooltips() {
  return __awaiter(this, void 0, void 0, function* () {
    yield loadPopperJs();
    initTooltips();
  });
}
if (typeof window !== "undefined" && typeof document !== "undefined") {
  document.addEventListener("DOMContentLoaded", () => {
    loadAndInitTooltips();
    const observer = new MutationObserver(() => {
      initTooltips();
    });
    observer.observe(document.body, {
      childList: true,
      subtree: true
    });
  });
}
var Tooltip = class {
  constructor(triggerElement, options = {}) {
    this.tooltipElement = null;
    this.tooltipInstance = null;
    this.triggerElement = triggerElement;
    this.options = {
      placement: options.placement || "top",
      tooltipClass: options.tooltipClass || "tooltip-default",
      content: options.content || ""
    };
    this.init();
  }
  init() {
    return __awaiter(this, void 0, void 0, function* () {
      yield loadPopperJs();
      this.triggerElement.addEventListener("mouseenter", this.showTooltip.bind(this));
      this.triggerElement.addEventListener("mouseleave", this.hideTooltip.bind(this));
    });
  }
  showTooltip() {
    return __awaiter(this, void 0, void 0, function* () {
      if (this.tooltipElement) return;
      this.tooltipElement = document.createElement("div");
      this.tooltipElement.className = this.options.tooltipClass;
      if (typeof this.options.content === "string") {
        this.tooltipElement.textContent = this.options.content;
      } else if (this.options.content instanceof HTMLElement) {
        const contentClone = this.options.content.cloneNode(true);
        contentClone.classList.remove("hidden");
        this.tooltipElement.appendChild(contentClone);
      } else {
        console.warn("No valid content provided for tooltip.");
        return;
      }
      document.body.appendChild(this.tooltipElement);
      this.tooltipInstance = createPopper(this.triggerElement, this.tooltipElement, {
        placement: this.options.placement,
        modifiers: [{
          name: "offset",
          options: {
            offset: [0, 8]
          }
        }]
      });
    });
  }
  hideTooltip() {
    if (this.tooltipInstance) {
      this.tooltipInstance.destroy();
      this.tooltipInstance = null;
    }
    if (this.tooltipElement) {
      this.tooltipElement.remove();
      this.tooltipElement = null;
    }
  }
  destroy() {
    this.triggerElement.removeEventListener("mouseenter", this.showTooltip.bind(this));
    this.triggerElement.removeEventListener("mouseleave", this.hideTooltip.bind(this));
    this.hideTooltip();
  }
};
var initializedTabs$1 = /* @__PURE__ */ new WeakSet();
function initTabs() {
  document.querySelectorAll(".tab-group").forEach((tabGroup) => {
    if (initializedTabs$1.has(tabGroup)) return;
    const tabList = tabGroup.querySelector("[role='tablist']");
    const tabLinks = (tabList === null || tabList === void 0 ? void 0 : tabList.querySelectorAll(".tab-link")) || [];
    const tabContents = tabGroup.querySelectorAll(".tab-content");
    const indicator = tabList === null || tabList === void 0 ? void 0 : tabList.querySelector(".tab-indicator");
    const isVertical = tabGroup.getAttribute("data-orientation") === "vertical";
    function updateIndicator(link) {
      const rect = link.getBoundingClientRect();
      const parentRect = tabList === null || tabList === void 0 ? void 0 : tabList.getBoundingClientRect();
      if (!parentRect || !indicator) return;
      requestAnimationFrame(() => {
        if (isVertical) {
          indicator.style.transform = `translateY(${rect.top - parentRect.top}px)`;
          indicator.style.height = `${rect.height}px`;
        } else {
          indicator.style.transform = `translateX(${rect.left - parentRect.left}px)`;
          indicator.style.width = `${rect.width}px`;
        }
        indicator.classList.remove("hidden");
        indicator.style.opacity = "1";
        indicator.style.scale = "1";
      });
    }
    function activateTab(link) {
      tabLinks.forEach((item) => item.classList.remove("active"));
      tabContents.forEach((content) => {
        content.classList.add("hidden");
        content.classList.remove("block");
      });
      link.classList.add("active");
      const targetContentId = link.getAttribute("data-tab-target");
      const targetContent = targetContentId ? document.getElementById(targetContentId) : null;
      if (targetContent) {
        targetContent.classList.add("block");
        targetContent.classList.remove("hidden");
      }
      updateIndicator(link);
    }
    function initializeTabGroup() {
      const activeLink = tabList === null || tabList === void 0 ? void 0 : tabList.querySelector(".tab-link.active");
      if (activeLink) {
        activateTab(activeLink);
      } else if (tabLinks.length > 0) {
        activateTab(tabLinks[0]);
      }
      tabLinks.forEach((link) => {
        link.addEventListener("click", (event) => {
          event.preventDefault();
          activateTab(link);
        });
      });
    }
    initializeTabGroup();
    initializedTabs$1.add(tabGroup);
  });
}
function cleanupTabs() {
  document.querySelectorAll(".tab-group").forEach((tabGroup) => {
    if (initializedTabs$1.has(tabGroup)) {
      const tabList = tabGroup.querySelector("[role='tablist']");
      const tabLinks = (tabList === null || tabList === void 0 ? void 0 : tabList.querySelectorAll(".tab-link")) || [];
      tabLinks.forEach((link) => {
        if (link.parentNode) {
          const clone = link.cloneNode(true);
          link.parentNode.replaceChild(clone, link);
        }
      });
      initializedTabs$1.delete(tabGroup);
    }
  });
}
if (typeof window !== "undefined") {
  document.addEventListener("DOMContentLoaded", () => {
    initTabs();
    const observer = new MutationObserver(() => {
      initTabs();
    });
    observer.observe(document.body, {
      childList: true,
      subtree: true
    });
  });
}
var initializedTabs = /* @__PURE__ */ new WeakSet();
var Tabs = class {
  /**
   * Creates a new Tabs instance.
   * @param tabGroup - The container element of the tab group.
   * @param options - Configuration options for the tabs.
   */
  constructor(tabGroup, options = {
    orientation: "horizontal"
  }) {
    var _a, _b, _c;
    if (initializedTabs.has(tabGroup)) {
      throw new Error("This tab group is already initialized.");
    }
    this.tabGroup = tabGroup;
    this.tabList = tabGroup.querySelector("[role='tablist']");
    this.tabLinks = Array.from(((_a = this.tabList) === null || _a === void 0 ? void 0 : _a.querySelectorAll(".tab-link")) || []);
    this.tabContents = Array.from(tabGroup.querySelectorAll(".tab-content"));
    this.indicator = ((_b = this.tabList) === null || _b === void 0 ? void 0 : _b.querySelector(".tab-indicator")) || null;
    this.orientation = options.orientation || "horizontal";
    this.defaultTabId = options.defaultTabId || ((_c = this.tabLinks[0]) === null || _c === void 0 ? void 0 : _c.id) || "tab1";
    this.initialize();
    initializedTabs.add(tabGroup);
  }
  /**
   * Initializes the tab group by setting up event listeners and activating the initial tab.
   */
  initialize() {
    var _a;
    const defaultTab = this.tabLinks.find((link) => link.id === this.defaultTabId);
    const activeTab = defaultTab || ((_a = this.tabList) === null || _a === void 0 ? void 0 : _a.querySelector(".tab-link.active")) || this.tabLinks[0];
    if (activeTab) {
      this.tabLinks.forEach((t) => t.classList.remove("active"));
      this.tabContents.forEach((c) => {
        c.classList.add("hidden");
        c.classList.remove("block");
      });
      setTimeout(() => {
        this.activateTab(activeTab.id);
      }, 300);
    }
    this.tabLinks.forEach((link) => {
      link.addEventListener("click", (event) => {
        event.preventDefault();
        this.activateTab(link.id);
      });
    });
  }
  /**
   * Updates the position of the tab indicator dynamically.
   * @param link - The active tab link element.
   */
  updateIndicator(link) {
    var _a;
    const rect = link.getBoundingClientRect();
    const parentRect = (_a = this.tabList) === null || _a === void 0 ? void 0 : _a.getBoundingClientRect();
    if (!parentRect || !this.indicator) return;
    requestAnimationFrame(() => {
      if (this.orientation === "vertical") {
        this.indicator.style.transform = `translateY(${rect.top - parentRect.top}px)`;
        this.indicator.style.height = `${rect.height}px`;
      } else {
        this.indicator.style.transform = `translateX(${rect.left - parentRect.left}px)`;
        this.indicator.style.width = `${rect.width}px`;
      }
      this.indicator.classList.remove("hidden");
      this.indicator.style.opacity = "1";
      this.indicator.style.scale = "1";
    });
  }
  /**
   * Activates the specified tab by its ID.
   * @param tabId - The ID of the tab to activate.
   */
  activateTab(tabId) {
    const tab = this.tabLinks.find((t) => t.id === tabId);
    const content = this.tabContents.find((c) => c.id === `${tabId}-content`);
    if (!tab || !content) {
      console.warn(`Tab or content with id ${tabId} not found`);
      return;
    }
    this.tabLinks.forEach((t) => t.classList.remove("active"));
    this.tabContents.forEach((c) => {
      c.classList.add("hidden");
      c.classList.remove("block");
    });
    tab.classList.add("active");
    content.classList.add("block");
    content.classList.remove("hidden");
    this.updateIndicator(tab);
  }
  /**
   * Cleans up the tab group by removing event listeners and resetting the DOM.
   */
  cleanup() {
    this.tabLinks.forEach((link) => {
      const clone = link.cloneNode(true);
      link.replaceWith(clone);
    });
    initializedTabs.delete(this.tabGroup);
  }
};
var initializedModals = /* @__PURE__ */ new WeakSet();
var activeModals = [];
function toggleModal(event) {
  const trigger = event.currentTarget;
  if (!trigger) return;
  const modalID = trigger.getAttribute("data-target");
  if (!modalID) return;
  const modal = document.querySelector(modalID);
  if (!modal) return;
  const isHidden = modal.classList.contains("pointer-events-none");
  modal.classList.toggle("opacity-0", !isHidden);
  modal.classList.toggle("opacity-100", isHidden);
  if (isHidden) {
    modal.classList.remove("pointer-events-none");
  } else {
    setTimeout(() => modal.classList.add("pointer-events-none"), 300);
  }
  const modalContent = modal.querySelector(isHidden ? ".scale-95" : ".scale-100");
  if (modalContent) {
    modalContent.classList.toggle("scale-95", !isHidden);
    modalContent.classList.toggle("scale-100", isHidden);
  }
  modal.setAttribute("aria-hidden", String(!isHidden));
  if (isHidden) {
    modal.addEventListener("click", closeOnOutsideClick);
    activeModals.push(modal);
  } else {
    modal.removeEventListener("click", closeOnOutsideClick);
    activeModals = activeModals.filter((m) => m !== modal);
  }
}
function closeModal(input) {
  let modal = null;
  if (input instanceof Event) {
    const trigger = input.currentTarget;
    if (!trigger) return;
    modal = trigger.closest(".fixed");
  } else {
    modal = input;
  }
  if (!modal) return;
  modal.classList.add("opacity-0");
  modal.classList.remove("opacity-100");
  const modalContent = modal.querySelector(".scale-100");
  if (modalContent) {
    modalContent.classList.add("scale-95");
    modalContent.classList.remove("scale-100");
  }
  setTimeout(() => {
    modal.classList.add("pointer-events-none");
    modal.setAttribute("aria-hidden", "true");
  }, 300);
  modal.removeEventListener("click", closeOnOutsideClick);
  activeModals = activeModals.filter((m) => m !== modal);
}
function closeOnOutsideClick(event) {
  const modal = event.currentTarget;
  if (!modal) return;
  const modalContent = modal.querySelector(".scale-100, .scale-95");
  if (!modalContent) return;
  if (!modalContent.contains(event.target)) {
    closeModal(modal);
  }
}
function initModal() {
  document.querySelectorAll("[data-toggle='modal']").forEach((trigger) => {
    if (!initializedModals.has(trigger)) {
      trigger.addEventListener("click", toggleModal);
      initializedModals.add(trigger);
    }
  });
  document.querySelectorAll("[data-dismiss='modal']").forEach((button) => {
    if (!initializedModals.has(button)) {
      button.addEventListener("click", closeModal);
      initializedModals.add(button);
    }
  });
}
function cleanupModals() {
  activeModals.forEach((modal) => {
    modal.removeEventListener("click", closeOnOutsideClick);
  });
  activeModals = [];
  initializedModals = /* @__PURE__ */ new WeakSet();
}
if (typeof window !== "undefined" && typeof document !== "undefined") {
  document.addEventListener("DOMContentLoaded", () => {
    initModal();
    const observer = new MutationObserver(() => {
      initModal();
    });
    observer.observe(document.body, {
      childList: true,
      subtree: true
    });
  });
}
var Modal = class {
  /**
   * Initialize the modal.
   * @param {HTMLElement} modalElement - The modal element.
   * @param {ModalConfig} [config={}] - Configuration options for the modal.
   */
  constructor(modalElement, config = {}) {
    this._isVisible = false;
    this.handleKeydown = (event) => {
      if (event.key === "Escape") {
        this.hide();
      }
    };
    this.handleOutsideClick = (event) => {
      const target = event.target;
      const modalContent = this._modalElement.firstElementChild;
      if (modalContent && !modalContent.contains(target)) {
        this.hide();
      }
    };
    this._modalElement = modalElement;
    this._config = Object.assign({
      keyboard: true,
      closeOnOutsideClick: true
    }, config);
    this.setupModal();
    setTimeout(() => {
      this.removeHiddenClass();
    }, 300);
  }
  /**
   * Show the modal.
   */
  show() {
    if (this._isVisible) return;
    this._isVisible = true;
    this._modalElement.classList.remove("opacity-0", "pointer-events-none");
    this._modalElement.classList.add("opacity-100");
    this._modalElement.setAttribute("aria-hidden", "false");
    if (this._config.keyboard) {
      document.addEventListener("keydown", this.handleKeydown);
    }
    if (this._config.closeOnOutsideClick) {
      document.addEventListener("click", this.handleOutsideClick, true);
    }
  }
  /**
   * Hide the modal.
   */
  hide() {
    if (!this._isVisible) return;
    this._isVisible = false;
    this._modalElement.classList.add("opacity-0", "pointer-events-none");
    this._modalElement.classList.remove("opacity-100");
    this._modalElement.setAttribute("aria-hidden", "true");
    if (this._config.keyboard) {
      document.removeEventListener("keydown", this.handleKeydown);
    }
    if (this._config.closeOnOutsideClick) {
      document.removeEventListener("click", this.handleOutsideClick, true);
    }
  }
  /**
   * Toggle the modal's visibility.
   */
  toggle() {
    this._isVisible ? this.hide() : this.show();
  }
  /**
   * Check if the modal is currently visible.
   * @returns {boolean}
   */
  isVisible() {
    return this._isVisible;
  }
  /**
   * Set up initial modal state.
   * Hides the modal if it's not already hidden.
   */
  setupModal() {
    const isHidden = this._modalElement.classList.contains("opacity-0") || this._modalElement.getAttribute("aria-hidden") === "true";
    this._isVisible = !isHidden;
    if (isHidden) {
      this._modalElement.classList.add("opacity-0", "pointer-events-none");
      this._modalElement.classList.remove("opacity-100");
    } else {
      this._modalElement.classList.remove("opacity-0", "pointer-events-none");
      this._modalElement.classList.add("opacity-100");
    }
    this._modalElement.setAttribute("aria-hidden", String(isHidden));
  }
  /**
   * Removes the hidden class from the modal element.
   * This is typically called before showing the modal.
   */
  removeHiddenClass() {
    this._modalElement.classList.remove("hidden");
  }
};
var initializedAccordionElements = /* @__PURE__ */ new WeakSet();
var handleIcons = (button, isExpanded, isRotating = false) => {
  const openIcon = button.querySelector("[data-accordion-icon-open]");
  const closeIcon = button.querySelector("[data-accordion-icon-close]");
  const rotatingIcon = button.querySelector("[data-accordion-icon]");
  if (openIcon && closeIcon) {
    openIcon.style.display = isExpanded ? "block" : "none";
    closeIcon.style.display = isExpanded ? "none" : "block";
  }
  if (rotatingIcon) {
    rotatingIcon.classList.toggle("rotate-180", isRotating ? isExpanded : !isExpanded);
  }
};
var toggleAccordionState = (targetElement, button, isExpanded) => {
  targetElement.style.maxHeight = isExpanded ? `${targetElement.scrollHeight}px` : "0";
  button.setAttribute("aria-expanded", String(isExpanded));
  handleIcons(button, isExpanded);
};
function toggleAccordion(event) {
  const button = event.currentTarget;
  if (button.getAttribute("aria-disabled") === "true") return;
  const targetID = button.dataset.accordionTarget;
  const parentElement = button.closest("[data-accordion-container]");
  const mode = parentElement === null || parentElement === void 0 ? void 0 : parentElement.dataset.accordionMode;
  if (targetID === null || targetID === void 0 ? void 0 : targetID.startsWith("#")) {
    const targetElement = document.querySelector(targetID);
    const isExpanded = button.getAttribute("aria-expanded") === "true";
    if (mode === "exclusive" && parentElement) {
      parentElement.querySelectorAll("[data-accordion-toggle]").forEach((otherButton) => {
        const otherTargetID = otherButton.dataset.accordionTarget;
        if (otherTargetID && otherTargetID !== targetID) {
          const otherElement = document.querySelector(otherTargetID);
          if (otherElement instanceof HTMLElement) {
            toggleAccordionState(otherElement, otherButton, false);
          }
        }
      });
    }
    if (targetElement) {
      toggleAccordionState(targetElement, button, !isExpanded);
    }
  }
}
function toggleAccordionById(targetId) {
  targetId = targetId.startsWith("#") ? targetId : `#${targetId}`;
  const targetElement = document.querySelector(targetId);
  const toggleButton = document.querySelector(`[data-accordion-target="${targetId}"]`);
  if ((toggleButton === null || toggleButton === void 0 ? void 0 : toggleButton.getAttribute("aria-disabled")) === "true" || !targetElement || !toggleButton) return;
  const isExpanded = toggleButton.getAttribute("aria-expanded") === "true";
  const parentElement = toggleButton.closest("[data-accordion-container]");
  const mode = parentElement === null || parentElement === void 0 ? void 0 : parentElement.dataset.accordionMode;
  if (mode === "exclusive" && parentElement) {
    parentElement.querySelectorAll("[data-accordion-toggle]").forEach((otherButton) => {
      const otherTargetID = otherButton.dataset.accordionTarget;
      if (typeof otherTargetID === "string" && otherTargetID !== targetId) {
        const otherElement = document.querySelector(otherTargetID);
        if (otherElement instanceof HTMLElement) {
          toggleAccordionState(otherElement, otherButton, false);
        }
      }
    });
  }
  toggleAccordionState(targetElement, toggleButton, !isExpanded);
}
function initAccordion() {
  document.querySelectorAll("[data-accordion-toggle]").forEach((button) => {
    if (!initializedAccordionElements.has(button)) {
      button.addEventListener("click", toggleAccordion);
      initializedAccordionElements.add(button);
      const targetID = button.dataset.accordionTarget;
      if (typeof targetID === "string") {
        const targetElement = document.querySelector(targetID);
        if (targetElement instanceof HTMLElement) {
          const isExpanded = button.getAttribute("aria-expanded") === "true";
          toggleAccordionState(targetElement, button, isExpanded);
        }
      }
    }
  });
}
function cleanupAccordions() {
  document.querySelectorAll("[data-accordion-toggle]").forEach((button) => {
    if (initializedAccordionElements.has(button)) {
      button.removeEventListener("click", toggleAccordion);
      initializedAccordionElements.delete(button);
    }
  });
}
if (typeof window !== "undefined") {
  window.toggleAccordionById = toggleAccordionById;
  document.addEventListener("DOMContentLoaded", () => {
    initAccordion();
    new MutationObserver(initAccordion).observe(document.body, {
      childList: true,
      subtree: true
    });
  });
}
var Accordion = class {
  constructor(container, options = {}) {
    this.initialized = /* @__PURE__ */ new WeakSet();
    this.toggleHandler = (event) => {
      const button = event.currentTarget;
      this.toggle(button);
    };
    this.container = container;
    this.options = options;
    this.init();
  }
  init() {
    const buttons = Array.from(this.container.children).filter((el) => el instanceof HTMLElement);
    buttons.forEach((button) => {
      const content = button.nextElementSibling;
      if (content) {
        this.initialized.add(button);
        button.addEventListener("click", this.toggleHandler);
        const isExpanded = this.options.allOpen || false;
        this.setAccordionState(button, content, isExpanded);
      }
    });
    if (this.options.allOpen) {
      this.showAll();
    }
  }
  resolveElement(element) {
    if (typeof element === "string") {
      return document.getElementById(element);
    }
    return element;
  }
  toggle(element) {
    const button = this.resolveElement(element);
    if (!button) return;
    const content = button.nextElementSibling;
    if (!content) return;
    const isExpanded = button.getAttribute("aria-expanded") === "true";
    if (this.options.exclusive) {
      Array.from(this.container.children).forEach((child) => {
        if (child instanceof HTMLElement && child !== button) {
          const otherContent = child.nextElementSibling;
          if (otherContent) {
            this.setAccordionState(child, otherContent, false);
          }
        }
      });
    }
    this.setAccordionState(button, content, !isExpanded);
  }
  show(element) {
    const button = this.resolveElement(element);
    if (!button) return;
    const content = button.nextElementSibling;
    if (!content) return;
    this.setAccordionState(button, content, true);
  }
  hide(element) {
    const button = this.resolveElement(element);
    if (!button) return;
    const content = button.nextElementSibling;
    if (!content) return;
    this.setAccordionState(button, content, false);
  }
  showAll() {
    Array.from(this.container.children).forEach((child) => {
      if (child instanceof HTMLElement) {
        const content = child.nextElementSibling;
        if (content) {
          this.setAccordionState(child, content, true);
        }
      }
    });
  }
  hideAll() {
    Array.from(this.container.children).forEach((child) => {
      if (child instanceof HTMLElement) {
        const content = child.nextElementSibling;
        if (content) {
          this.setAccordionState(child, content, false);
        }
      }
    });
  }
  cleanup() {
    Array.from(this.container.children).forEach((button) => {
      if (button instanceof HTMLElement && this.initialized.has(button)) {
        button.removeEventListener("click", this.toggleHandler);
        this.initialized.delete(button);
      }
    });
  }
  setAccordionState(button, content, isExpanded) {
    content.style.maxHeight = isExpanded ? `${content.scrollHeight}px` : "0";
    button.setAttribute("aria-expanded", String(isExpanded));
    const openIcon = button.querySelector("[data-accordion-icon-open]");
    const closeIcon = button.querySelector("[data-accordion-icon-close]");
    if (openIcon) {
      openIcon.style.display = isExpanded ? "block" : "none";
    }
    if (closeIcon) {
      closeIcon.style.display = isExpanded ? "none" : "block";
    }
    const icon = button.querySelector("[data-accordion-icon]");
    if (icon) {
      icon.classList.toggle("rotate-180", isExpanded);
    }
  }
};
var initializedStepperElements = /* @__PURE__ */ new WeakSet();
function updateStepperState(container) {
  const steps = container.querySelectorAll("[data-step]");
  const stepContents = container.querySelectorAll("[data-step-content]");
  const prevButtons = container.querySelectorAll("[data-stepper-prev]");
  const nextButtons = container.querySelectorAll("[data-stepper-next]");
  let currentStep = parseInt(container.getAttribute("data-step") || "1", 10);
  function updateState() {
    steps.forEach((step, index2) => {
      const stepNumber = index2 + 1;
      step.setAttribute("data-active", String(stepNumber === currentStep));
      step.setAttribute("data-completed", String(stepNumber < currentStep));
      step.setAttribute("aria-disabled", String(stepNumber > currentStep));
    });
    stepContents.forEach((content) => {
      const contentStep = parseInt(content.getAttribute("data-step-content") || "0", 10);
      if (contentStep === currentStep) {
        content.classList.remove("hidden");
      } else {
        content.classList.add("hidden");
      }
    });
    prevButtons.forEach((button) => {
      button.disabled = currentStep === 1;
    });
    nextButtons.forEach((button) => {
      button.disabled = currentStep === steps.length;
    });
  }
  function onNextButtonClick() {
    if (currentStep < steps.length) {
      currentStep++;
      container.setAttribute("data-step", String(currentStep));
      updateState();
    }
  }
  function onPrevButtonClick() {
    if (currentStep > 1) {
      currentStep--;
      container.setAttribute("data-step", String(currentStep));
      updateState();
    }
  }
  nextButtons.forEach((button) => {
    button.addEventListener("click", onNextButtonClick);
  });
  prevButtons.forEach((button) => {
    button.addEventListener("click", onPrevButtonClick);
  });
  container.__stepperCleanup = () => {
    nextButtons.forEach((button) => {
      button.removeEventListener("click", onNextButtonClick);
    });
    prevButtons.forEach((button) => {
      button.removeEventListener("click", onPrevButtonClick);
    });
  };
  updateState();
}
function initStepper() {
  document.querySelectorAll("[data-stepper-container]").forEach((container) => {
    if (!initializedStepperElements.has(container)) {
      initializedStepperElements.add(container);
      const initialStep = parseInt(container.getAttribute("data-initial-step") || "1", 10);
      container.setAttribute("data-step", String(initialStep));
      updateStepperState(container);
    }
  });
}
function cleanupSteppers() {
  document.querySelectorAll("[data-stepper-container]").forEach((container) => {
    if (container.__stepperCleanup) {
      container.__stepperCleanup();
      delete container.__stepperCleanup;
    }
    initializedStepperElements.delete(container);
  });
}
if (typeof window !== "undefined") {
  document.addEventListener("DOMContentLoaded", () => {
    initStepper();
    new MutationObserver(initStepper).observe(document.body, {
      childList: true,
      subtree: true
    });
  });
}
var Stepper = class {
  constructor(config) {
    this.steps = config.stepElements;
    this.contents = config.contentElements;
    this.prevButton = config.prevButton;
    this.nextButton = config.nextButton;
    this.currentStep = config.initialStep || 1;
    this.updateState();
    this.prevButton.addEventListener("click", () => this.prev());
    this.nextButton.addEventListener("click", () => this.next());
  }
  updateState() {
    this.steps.forEach((step, index2) => {
      const stepNumber = index2 + 1;
      step.dataset.active = String(stepNumber === this.currentStep);
      step.dataset.completed = String(stepNumber < this.currentStep);
      step.setAttribute("aria-disabled", String(stepNumber > this.currentStep));
    });
    this.contents.forEach((content, index2) => {
      content.classList.toggle("hidden", index2 + 1 !== this.currentStep);
    });
    this.prevButton.disabled = this.currentStep === 1;
    this.nextButton.disabled = this.currentStep === this.steps.length;
  }
  next() {
    if (this.currentStep < this.steps.length) {
      this.currentStep++;
      this.updateState();
    }
  }
  prev() {
    if (this.currentStep > 1) {
      this.currentStep--;
      this.updateState();
    }
  }
  goToStep(step) {
    if (step >= 1 && step <= this.steps.length) {
      this.currentStep = step;
      this.updateState();
    }
  }
  getCurrentStep() {
    return this.currentStep;
  }
  destroy() {
    this.prevButton.removeEventListener("click", () => this.prev());
    this.nextButton.removeEventListener("click", () => this.next());
  }
};
var MaterialTailwind = {
  initAlert,
  initCollapse,
  initDropdowns,
  cleanupDropdowns,
  initPopovers,
  cleanupPopovers,
  initTooltips,
  cleanupTooltips,
  initTabs,
  cleanupTabs,
  initModal,
  cleanupModals,
  initAccordion,
  cleanupAccordions,
  toggleAccordionById,
  initStepper,
  cleanupSteppers,
  initGallery,
  cleanupGallery
};
function initMaterialTailwind() {
  initAlert();
  initCollapse();
  initTabs();
  initModal();
  initAccordion();
  initStepper();
  initGallery();
  loadPopperJs().then(() => {
    initDropdowns();
    initPopovers();
    initTooltips();
  }).catch((error) => {
    console.error("Failed to load Popper.js:", error);
  });
}
if (typeof window !== "undefined" && typeof document !== "undefined") {
  document.addEventListener("DOMContentLoaded", () => {
    initMaterialTailwind();
    const observer = new MutationObserver(() => {
      initAlert();
      initCollapse();
      initAccordion();
      initStepper();
      initGallery();
      initTabs();
      initModal();
      initDropdowns();
      initPopovers();
      initTooltips();
    });
    observer.observe(document.body, {
      childList: true,
      subtree: true
    });
    window.MaterialTailwind = Object.assign(Object.assign({}, MaterialTailwind), {
      initMaterialTailwind
    });
  });
}
var index = Object.assign(Object.assign({}, MaterialTailwind), {
  initMaterialTailwind
});
export {
  Accordion,
  Collapse,
  Dropdown2 as Dropdown,
  MaterialTailwind,
  Modal,
  Popover,
  Stepper,
  Tabs,
  Tooltip,
  cleanupAccordions,
  cleanupDropdowns,
  cleanupGallery,
  cleanupModals,
  cleanupPopovers,
  cleanupSteppers,
  cleanupTabs,
  cleanupTooltips,
  index as default,
  initAccordion,
  initAlert,
  initCollapse,
  initDropdowns,
  initGallery,
  initMaterialTailwind,
  initModal,
  initPopovers,
  initStepper,
  initTabs,
  initTooltips,
  toggleAccordionById
};
/*! Bundled license information:

@material-tailwind/html/dist/material-tailwind.esm.js:
  (*!
   * Material Tailwind JavaScript/TypeScript Library v3.0.0-beta.7
   * (c) 2025 Material Tailwind - Creative Tim
   * Released under the MIT License.
   * Written in TypeScript, usable in both JavaScript and TypeScript projects.
   *)
*/
//# sourceMappingURL=@material-tailwind_html.js.map
