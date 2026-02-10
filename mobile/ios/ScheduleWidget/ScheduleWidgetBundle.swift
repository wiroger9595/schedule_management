//
//  ScheduleWidgetBundle.swift
//  ScheduleWidget
//
//  Created by chen robert on 2026/2/2.
//

import WidgetKit
import SwiftUI

@main
struct ScheduleWidgetBundle: WidgetBundle {
    var body: some Widget {
        ScheduleWidget()
        ScheduleWidgetControl()
    }
}
