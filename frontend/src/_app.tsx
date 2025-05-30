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
# SPDX-License-Identifier: Apache-2.0
*/
import { Route, Routes, Navigate } from "react-router-dom";
import urls from "./urls";
import SessionPage from "./pages/session/details";
// import DashboardPage from "./pages/dashboard";

function App() {
  return (
    <Routes>
      <Route path={urls.session.getHref()} element={<SessionPage />} />
      <Route path="*" element={<Navigate to={urls.session.getHref()} />} />
      {/* <Route path="/" element={<DashboardPage />} /> */}
      {/* <Route path={urls.dashboard.getHref()} element={<DashboardPage />} /> */}
    </Routes>
  );
}

export default App;
