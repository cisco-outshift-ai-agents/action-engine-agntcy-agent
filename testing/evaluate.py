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
from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCaseParams, LLMTestCase
from typing import List, Optional
from dotenv import load_dotenv

load_dotenv()


def evaluate_actions(
    task: str, actual_actions: List[str], expected_actions: List[str]
) -> GEval:
    """
    Compare expected and actual actions using Geval.

    Args:
        task: The task description
        actual_actions: List of actual action representations
        expected_actions: List of expected action representations

    Returns:
        GEval metric object containing score and reason
    """
    correctness_metric = GEval(
        name="Correctness",
        criteria="""You are evaluating if two action sequences are equivalent. When comparing element types in action representations, consider the following equivalences:

                    1. Input/Interaction elements:
                    - [input], [textbox], and [searchbox] when used with TYPE action are equivalent
                    - [button], [link], and clickable [div] when used with CLICK action are equivalent
                    - [select], [combobox], and [option] when used with selection actions are equivalent

                    2. Container/Structural elements:
                    - Any container element ([div], [span], [section], etc.) should be judged based on its action and description, not its HTML tag

                    3. Custom elements:
                    - Custom elements like [adc-button], [hp-input-button] should be judged based on their semantic role (e.g., if it's used as a button, treat it as [button])

                    Focus on whether they achieve the same interactions, not whether they use identical element types.
                    """,
        evaluation_params=[
            LLMTestCaseParams.INPUT,
            LLMTestCaseParams.ACTUAL_OUTPUT,
            LLMTestCaseParams.EXPECTED_OUTPUT,
        ],
    )

    test_case = LLMTestCase(
        input=task,
        actual_output=actual_actions,
        expected_output=expected_actions,
    )

    correctness_metric.measure(test_case)
    return correctness_metric
