#[cfg(feature = "serde")]
use serde::{Deserialize, Serialize};


#[link(name = "cyberrunner_interfaces__rosidl_typesupport_c")]
extern "C" {
    fn rosidl_typesupport_c__get_message_type_support_handle__cyberrunner_interfaces__msg__DynamixelVel() -> *const std::ffi::c_void;
}

#[link(name = "cyberrunner_interfaces__rosidl_generator_c")]
extern "C" {
    fn cyberrunner_interfaces__msg__DynamixelVel__init(msg: *mut DynamixelVel) -> bool;
    fn cyberrunner_interfaces__msg__DynamixelVel__Sequence__init(seq: *mut rosidl_runtime_rs::Sequence<DynamixelVel>, size: usize) -> bool;
    fn cyberrunner_interfaces__msg__DynamixelVel__Sequence__fini(seq: *mut rosidl_runtime_rs::Sequence<DynamixelVel>);
    fn cyberrunner_interfaces__msg__DynamixelVel__Sequence__copy(in_seq: &rosidl_runtime_rs::Sequence<DynamixelVel>, out_seq: *mut rosidl_runtime_rs::Sequence<DynamixelVel>) -> bool;
}

// Corresponds to cyberrunner_interfaces__msg__DynamixelVel
#[cfg_attr(feature = "serde", derive(Deserialize, Serialize))]

/// Velocity commands for the dynamixels  TODO: refactor

#[repr(C)]
#[derive(Clone, Debug, PartialEq, PartialOrd)]
pub struct DynamixelVel {

    // This member is not documented.
    #[allow(missing_docs)]
    pub vel_1: f64,


    // This member is not documented.
    #[allow(missing_docs)]
    pub vel_2: f64,

}



impl Default for DynamixelVel {
  fn default() -> Self {
    unsafe {
      let mut msg = std::mem::zeroed();
      if !cyberrunner_interfaces__msg__DynamixelVel__init(&mut msg as *mut _) {
        panic!("Call to cyberrunner_interfaces__msg__DynamixelVel__init() failed");
      }
      msg
    }
  }
}

impl rosidl_runtime_rs::SequenceAlloc for DynamixelVel {
  fn sequence_init(seq: &mut rosidl_runtime_rs::Sequence<Self>, size: usize) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { cyberrunner_interfaces__msg__DynamixelVel__Sequence__init(seq as *mut _, size) }
  }
  fn sequence_fini(seq: &mut rosidl_runtime_rs::Sequence<Self>) {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { cyberrunner_interfaces__msg__DynamixelVel__Sequence__fini(seq as *mut _) }
  }
  fn sequence_copy(in_seq: &rosidl_runtime_rs::Sequence<Self>, out_seq: &mut rosidl_runtime_rs::Sequence<Self>) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { cyberrunner_interfaces__msg__DynamixelVel__Sequence__copy(in_seq, out_seq as *mut _) }
  }
}

impl rosidl_runtime_rs::Message for DynamixelVel {
  type RmwMsg = Self;
  fn into_rmw_message(msg_cow: std::borrow::Cow<'_, Self>) -> std::borrow::Cow<'_, Self::RmwMsg> { msg_cow }
  fn from_rmw_message(msg: Self::RmwMsg) -> Self { msg }
}

impl rosidl_runtime_rs::RmwMessage for DynamixelVel where Self: Sized {
  const TYPE_NAME: &'static str = "cyberrunner_interfaces/msg/DynamixelVel";
  fn get_type_support() -> *const std::ffi::c_void {
    // SAFETY: No preconditions for this function.
    unsafe { rosidl_typesupport_c__get_message_type_support_handle__cyberrunner_interfaces__msg__DynamixelVel() }
  }
}


#[link(name = "cyberrunner_interfaces__rosidl_typesupport_c")]
extern "C" {
    fn rosidl_typesupport_c__get_message_type_support_handle__cyberrunner_interfaces__msg__StateEstimate() -> *const std::ffi::c_void;
}

#[link(name = "cyberrunner_interfaces__rosidl_generator_c")]
extern "C" {
    fn cyberrunner_interfaces__msg__StateEstimate__init(msg: *mut StateEstimate) -> bool;
    fn cyberrunner_interfaces__msg__StateEstimate__Sequence__init(seq: *mut rosidl_runtime_rs::Sequence<StateEstimate>, size: usize) -> bool;
    fn cyberrunner_interfaces__msg__StateEstimate__Sequence__fini(seq: *mut rosidl_runtime_rs::Sequence<StateEstimate>);
    fn cyberrunner_interfaces__msg__StateEstimate__Sequence__copy(in_seq: &rosidl_runtime_rs::Sequence<StateEstimate>, out_seq: *mut rosidl_runtime_rs::Sequence<StateEstimate>) -> bool;
}

// Corresponds to cyberrunner_interfaces__msg__StateEstimate
#[cfg_attr(feature = "serde", derive(Deserialize, Serialize))]


// This struct is not documented.
#[allow(missing_docs)]

#[repr(C)]
#[derive(Clone, Debug, PartialEq, PartialOrd)]
pub struct StateEstimate {

    // This member is not documented.
    #[allow(missing_docs)]
    pub x_b: f64,


    // This member is not documented.
    #[allow(missing_docs)]
    pub y_b: f64,


    // This member is not documented.
    #[allow(missing_docs)]
    pub x_b_dot: f64,


    // This member is not documented.
    #[allow(missing_docs)]
    pub y_b_dot: f64,


    // This member is not documented.
    #[allow(missing_docs)]
    pub alpha: f64,


    // This member is not documented.
    #[allow(missing_docs)]
    pub beta: f64,

}



impl Default for StateEstimate {
  fn default() -> Self {
    unsafe {
      let mut msg = std::mem::zeroed();
      if !cyberrunner_interfaces__msg__StateEstimate__init(&mut msg as *mut _) {
        panic!("Call to cyberrunner_interfaces__msg__StateEstimate__init() failed");
      }
      msg
    }
  }
}

impl rosidl_runtime_rs::SequenceAlloc for StateEstimate {
  fn sequence_init(seq: &mut rosidl_runtime_rs::Sequence<Self>, size: usize) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { cyberrunner_interfaces__msg__StateEstimate__Sequence__init(seq as *mut _, size) }
  }
  fn sequence_fini(seq: &mut rosidl_runtime_rs::Sequence<Self>) {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { cyberrunner_interfaces__msg__StateEstimate__Sequence__fini(seq as *mut _) }
  }
  fn sequence_copy(in_seq: &rosidl_runtime_rs::Sequence<Self>, out_seq: &mut rosidl_runtime_rs::Sequence<Self>) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { cyberrunner_interfaces__msg__StateEstimate__Sequence__copy(in_seq, out_seq as *mut _) }
  }
}

impl rosidl_runtime_rs::Message for StateEstimate {
  type RmwMsg = Self;
  fn into_rmw_message(msg_cow: std::borrow::Cow<'_, Self>) -> std::borrow::Cow<'_, Self::RmwMsg> { msg_cow }
  fn from_rmw_message(msg: Self::RmwMsg) -> Self { msg }
}

impl rosidl_runtime_rs::RmwMessage for StateEstimate where Self: Sized {
  const TYPE_NAME: &'static str = "cyberrunner_interfaces/msg/StateEstimate";
  fn get_type_support() -> *const std::ffi::c_void {
    // SAFETY: No preconditions for this function.
    unsafe { rosidl_typesupport_c__get_message_type_support_handle__cyberrunner_interfaces__msg__StateEstimate() }
  }
}


#[link(name = "cyberrunner_interfaces__rosidl_typesupport_c")]
extern "C" {
    fn rosidl_typesupport_c__get_message_type_support_handle__cyberrunner_interfaces__msg__StateEstimateSub() -> *const std::ffi::c_void;
}

#[link(name = "cyberrunner_interfaces__rosidl_generator_c")]
extern "C" {
    fn cyberrunner_interfaces__msg__StateEstimateSub__init(msg: *mut StateEstimateSub) -> bool;
    fn cyberrunner_interfaces__msg__StateEstimateSub__Sequence__init(seq: *mut rosidl_runtime_rs::Sequence<StateEstimateSub>, size: usize) -> bool;
    fn cyberrunner_interfaces__msg__StateEstimateSub__Sequence__fini(seq: *mut rosidl_runtime_rs::Sequence<StateEstimateSub>);
    fn cyberrunner_interfaces__msg__StateEstimateSub__Sequence__copy(in_seq: &rosidl_runtime_rs::Sequence<StateEstimateSub>, out_seq: *mut rosidl_runtime_rs::Sequence<StateEstimateSub>) -> bool;
}

// Corresponds to cyberrunner_interfaces__msg__StateEstimateSub
#[cfg_attr(feature = "serde", derive(Deserialize, Serialize))]


// This struct is not documented.
#[allow(missing_docs)]

#[repr(C)]
#[derive(Clone, Debug, PartialEq, PartialOrd)]
pub struct StateEstimateSub {

    // This member is not documented.
    #[allow(missing_docs)]
    pub state: super::super::msg::rmw::StateEstimate,


    // This member is not documented.
    #[allow(missing_docs)]
    pub subimg: sensor_msgs::msg::rmw::Image,

}



impl Default for StateEstimateSub {
  fn default() -> Self {
    unsafe {
      let mut msg = std::mem::zeroed();
      if !cyberrunner_interfaces__msg__StateEstimateSub__init(&mut msg as *mut _) {
        panic!("Call to cyberrunner_interfaces__msg__StateEstimateSub__init() failed");
      }
      msg
    }
  }
}

impl rosidl_runtime_rs::SequenceAlloc for StateEstimateSub {
  fn sequence_init(seq: &mut rosidl_runtime_rs::Sequence<Self>, size: usize) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { cyberrunner_interfaces__msg__StateEstimateSub__Sequence__init(seq as *mut _, size) }
  }
  fn sequence_fini(seq: &mut rosidl_runtime_rs::Sequence<Self>) {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { cyberrunner_interfaces__msg__StateEstimateSub__Sequence__fini(seq as *mut _) }
  }
  fn sequence_copy(in_seq: &rosidl_runtime_rs::Sequence<Self>, out_seq: &mut rosidl_runtime_rs::Sequence<Self>) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { cyberrunner_interfaces__msg__StateEstimateSub__Sequence__copy(in_seq, out_seq as *mut _) }
  }
}

impl rosidl_runtime_rs::Message for StateEstimateSub {
  type RmwMsg = Self;
  fn into_rmw_message(msg_cow: std::borrow::Cow<'_, Self>) -> std::borrow::Cow<'_, Self::RmwMsg> { msg_cow }
  fn from_rmw_message(msg: Self::RmwMsg) -> Self { msg }
}

impl rosidl_runtime_rs::RmwMessage for StateEstimateSub where Self: Sized {
  const TYPE_NAME: &'static str = "cyberrunner_interfaces/msg/StateEstimateSub";
  fn get_type_support() -> *const std::ffi::c_void {
    // SAFETY: No preconditions for this function.
    unsafe { rosidl_typesupport_c__get_message_type_support_handle__cyberrunner_interfaces__msg__StateEstimateSub() }
  }
}


