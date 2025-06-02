/*
# Copyright 2025 Cisco Systems, Inc. and its affiliates
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# SPDX-License-Identifier: Apache-2.0"
*/
const getElementSemanticInfo = (element) => {
  if (!element) return "unknown element";

  // Get basic element information
  const tag = element.tagName.toLowerCase();
  const id = element.id;
  const classes = Array.from(element.classList).join(' ');

  // Get text content, trimmed and truncated
  const text = element.textContent?.trim().substring(0, 50);

  // Get specific attributes based on element type
  const role = element.getAttribute('aria-role') || element.getAttribute('role');
  const name = element.getAttribute('name');
  const type = element.getAttribute('type');
  const placeholder = element.getAttribute('placeholder');
  const title = element.getAttribute('title');
  const href = element.getAttribute('href');
  const value = element.value;
  const label = element.getAttribute('aria-label') ||
    element.getAttribute('label') ||
    element.closest('label')?.textContent?.trim();

  // Build semantic description
  let semanticParts = [];

  // Add role or tag
  if (role) {
    semanticParts.push(`${role}`);
  } else {
    semanticParts.push(tag);
  }

  // Add identifier if present
  if (id) {
    semanticParts.push(`#${id}`);
  }

  // Add element-specific information
  switch (tag) {
    case 'input':
      if (type) semanticParts.push(`type="${type}"`);
      if (name) semanticParts.push(`name="${name}"`);
      if (placeholder) semanticParts.push(`placeholder="${placeholder}"`);
      if (label) semanticParts.push(`label="${label}"`);
      if (value) semanticParts.push(`value="${value}"`);
      break;
    case 'button':
      if (text) semanticParts.push(`text="${text}"`);
      break;
    case 'a':
      if (text) semanticParts.push(`text="${text}"`);
      if (href) {
        const shortHref = href.length > 30 ? href.substring(0, 30) + '...' : href;
        semanticParts.push(`href="${shortHref}"`);
      }
      break;
    case 'select':
      if (name) semanticParts.push(`name="${name}"`);
      if (label) semanticParts.push(`label="${label}"`);
      break;
    default:
      if (text) semanticParts.push(`text="${text}"`);
  }

  // Add important ARIA attributes
  const ariaAttributes = [
    'aria-label', 'aria-description', 'aria-expanded',
    'aria-selected', 'aria-checked', 'aria-pressed'
  ];

  for (const attr of ariaAttributes) {
    const value = element.getAttribute(attr);
    if (value) {
      semanticParts.push(`${attr}="${value}"`);
    }
  }

  // Get parent context if helpful
  const parentContext = getParentContext(element);
  if (parentContext) {
    semanticParts.push(`in ${parentContext}`);
  }

  return semanticParts.join(' ');
};

const getParentContext = (element) => {
  const contextualParents = [];
  let current = element.parentElement;
  let depth = 0;

  while (current && depth < 2) {
    if (current.id || current.role || current.getAttribute('aria-label')) {
      const id = current.id;
      const role = current.getAttribute('role');
      const label = current.getAttribute('aria-label');

      if (id) contextualParents.push(`#${id}`);
      if (role) contextualParents.push(role);
      if (label) contextualParents.push(`"${label}"`);

      depth++;
    }

    current = current.parentElement;
  }

  return contextualParents.length > 0 ? contextualParents.join(' > ') : '';
};

const sendEventDetails = (eventDetails) => {
  console.log('Event details:', eventDetails);

  fetch('http://localhost:7788/api/event-log', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(eventDetails)
  })
    .then(response => response.json())
    .then(data => console.log('Event log:', data))
    .catch(error => console.error('Error:', error));
};

const generateActionReprs = (event) => {
  const action = event ? event.event : null;
  const result = {
    current_state: {
      prev_action_evaluation: "Success",
      important_contents: "",
      task_progress: "",
      future_plans: "",
      thought: "",
      summary: ""
    },
    action: []
  }

  switch (action) {
    case 'click':
      result.action.push({ click_element: { index: 0, xpath: null } });
      return result;
    case 'input':
      result.action.push({ input_text: { index: 0, text: event.value, xpath: null } });
      return result;
    case 'scroll':
      result.action.push({ scroll_down: { amount: null } });
      return result;
    case 'keydown':
      // TODO: Need to throttle this event and wait for the user to finish typing
      result.action.push({ send_keys: { keys: event.value } });
      return result;
    default:
      return result;
  }
};

const getFullEventDetails = (event) => {
  const action_uid = generateUUID();
  // const raw_html = document.documentElement.outerHTML;
  // Removing this to now because it's too large
  const raw_html = ""
  const website = window.location.hostname;
  const domain = window.location.hostname.split('.').slice(-2).join('.');
  const subdomain = window.location.hostname.split('.').slice(0, -2).join('.');
  const operation = event ? { original_op: event.event, value: event.value, op: event.event, target: event.target } : null;
  const cleaned_html = '';
  const pos_candidates = [];
  const neg_candidates = [];
  const annotation_id = '';
  const confirmed_task = ''
  const screenshot = '';
  const action_reprs = generateActionReprs(event);
  const target_action_index = '';
  const target_action = event.event;

  return {
    action_uid,
    raw_html,
    cleaned_html,
    operation,
    pos_candidates,
    neg_candidates,
    website,
    domain,
    subdomain,
    annotation_id,
    confirmed_task,
    screenshot,
    action_reprs,
    target_action_index,
    target_action
  };
};

const generateUUID = () => {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
    const r = (Math.random() * 16) | 0,
      v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
};

document.addEventListener('DOMContentLoaded', function () {
  // Event listener for click events
  document.addEventListener('click', function (event) {
    const target = event.target;
    const eventDetails = getFullEventDetails({
      event: 'click',
      target: getElementSemanticInfo(target)
    });
    sendEventDetails(eventDetails);
  });

  // Event listener for input events
  document.addEventListener('input', function (event) {
    const target = event.target;
    const eventDetails = getFullEventDetails({
      event: 'input',
      target: getElementSemanticInfo(target),
      value: target.value
    });
    sendEventDetails(eventDetails);
  });

  // Event listener for scroll events
  document.addEventListener('scroll', function (event) {
    const eventDetails = getFullEventDetails({
      event: 'scroll',
      target: 'page' // Since scroll doesn't have a specific target
    });
    sendEventDetails(eventDetails);
  });

  // Event listener for keydown events
  document.addEventListener('keydown', function (event) {
    const target = event.target;
    const eventDetails = getFullEventDetails({
      event: 'keydown',
      target: getElementSemanticInfo(target),
      value: event.key
    });
    sendEventDetails(eventDetails);
  });
});