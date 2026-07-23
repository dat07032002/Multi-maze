#[cfg(feature = "serde")]
use serde::{Deserialize, Serialize};



// Corresponds to cyberrunner_interfaces__msg__DynamixelVel
/// Velocity commands for the dynamixels  TODO: refactor

#[cfg_attr(feature = "serde", derive(Deserialize, Serialize))]
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
    <Self as rosidl_runtime_rs::Message>::from_rmw_message(super::msg::rmw::DynamixelVel::default())
  }
}

impl rosidl_runtime_rs::Message for DynamixelVel {
  type RmwMsg = super::msg::rmw::DynamixelVel;

  fn into_rmw_message(msg_cow: std::borrow::Cow<'_, Self>) -> std::borrow::Cow<'_, Self::RmwMsg> {
    match msg_cow {
      std::borrow::Cow::Owned(msg) => std::borrow::Cow::Owned(Self::RmwMsg {
        vel_1: msg.vel_1,
        vel_2: msg.vel_2,
      }),
      std::borrow::Cow::Borrowed(msg) => std::borrow::Cow::Owned(Self::RmwMsg {
      vel_1: msg.vel_1,
      vel_2: msg.vel_2,
      })
    }
  }

  fn from_rmw_message(msg: Self::RmwMsg) -> Self {
    Self {
      vel_1: msg.vel_1,
      vel_2: msg.vel_2,
    }
  }
}


// Corresponds to cyberrunner_interfaces__msg__StateEstimate

// This struct is not documented.
#[allow(missing_docs)]

#[cfg_attr(feature = "serde", derive(Deserialize, Serialize))]
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
    <Self as rosidl_runtime_rs::Message>::from_rmw_message(super::msg::rmw::StateEstimate::default())
  }
}

impl rosidl_runtime_rs::Message for StateEstimate {
  type RmwMsg = super::msg::rmw::StateEstimate;

  fn into_rmw_message(msg_cow: std::borrow::Cow<'_, Self>) -> std::borrow::Cow<'_, Self::RmwMsg> {
    match msg_cow {
      std::borrow::Cow::Owned(msg) => std::borrow::Cow::Owned(Self::RmwMsg {
        x_b: msg.x_b,
        y_b: msg.y_b,
        x_b_dot: msg.x_b_dot,
        y_b_dot: msg.y_b_dot,
        alpha: msg.alpha,
        beta: msg.beta,
      }),
      std::borrow::Cow::Borrowed(msg) => std::borrow::Cow::Owned(Self::RmwMsg {
      x_b: msg.x_b,
      y_b: msg.y_b,
      x_b_dot: msg.x_b_dot,
      y_b_dot: msg.y_b_dot,
      alpha: msg.alpha,
      beta: msg.beta,
      })
    }
  }

  fn from_rmw_message(msg: Self::RmwMsg) -> Self {
    Self {
      x_b: msg.x_b,
      y_b: msg.y_b,
      x_b_dot: msg.x_b_dot,
      y_b_dot: msg.y_b_dot,
      alpha: msg.alpha,
      beta: msg.beta,
    }
  }
}


// Corresponds to cyberrunner_interfaces__msg__StateEstimateSub

// This struct is not documented.
#[allow(missing_docs)]

#[cfg_attr(feature = "serde", derive(Deserialize, Serialize))]
#[derive(Clone, Debug, PartialEq, PartialOrd)]
pub struct StateEstimateSub {

    // This member is not documented.
    #[allow(missing_docs)]
    pub state: super::msg::StateEstimate,


    // This member is not documented.
    #[allow(missing_docs)]
    pub subimg: sensor_msgs::msg::Image,

}



impl Default for StateEstimateSub {
  fn default() -> Self {
    <Self as rosidl_runtime_rs::Message>::from_rmw_message(super::msg::rmw::StateEstimateSub::default())
  }
}

impl rosidl_runtime_rs::Message for StateEstimateSub {
  type RmwMsg = super::msg::rmw::StateEstimateSub;

  fn into_rmw_message(msg_cow: std::borrow::Cow<'_, Self>) -> std::borrow::Cow<'_, Self::RmwMsg> {
    match msg_cow {
      std::borrow::Cow::Owned(msg) => std::borrow::Cow::Owned(Self::RmwMsg {
        state: super::msg::StateEstimate::into_rmw_message(std::borrow::Cow::Owned(msg.state)).into_owned(),
        subimg: sensor_msgs::msg::Image::into_rmw_message(std::borrow::Cow::Owned(msg.subimg)).into_owned(),
      }),
      std::borrow::Cow::Borrowed(msg) => std::borrow::Cow::Owned(Self::RmwMsg {
        state: super::msg::StateEstimate::into_rmw_message(std::borrow::Cow::Borrowed(&msg.state)).into_owned(),
        subimg: sensor_msgs::msg::Image::into_rmw_message(std::borrow::Cow::Borrowed(&msg.subimg)).into_owned(),
      })
    }
  }

  fn from_rmw_message(msg: Self::RmwMsg) -> Self {
    Self {
      state: super::msg::StateEstimate::from_rmw_message(msg.state),
      subimg: sensor_msgs::msg::Image::from_rmw_message(msg.subimg),
    }
  }
}


